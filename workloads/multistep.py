"""Reference calculations and offline validation for scripted multistep tasks.

python -m workloads.multistep --tasks workloads/tasks/v1/multistep.jsonl
This does not execute model requests, agent tools, or a quality evaluator.
"""
import argparse
import json
from pathlib import Path


def reference_answer(task):
    fixtures = task["tool_fixtures"]
    mode = task["scenario"]
    if task["subtype"] == "sales_analysis":
        rows = list(fixtures.values())
        regions = [row["region"] for row in rows]
        if len(regions) != len(set(regions)):
            raise ValueError("Duplicate sales regions")
        if mode == "net_total":
            net = {r["region"]: r["gross_sales_usd"] - r["refunds_usd"] for r in rows}
            leader = min(net, key=lambda region: (-net[region], region))
            return {"total_net_sales_usd": sum(net.values()), "largest_region": leader,
                    "largest_region_net_sales_usd": net[leader]}
        if mode == "target_gap":
            net = {r["region"]: r["gross_sales_usd"] - r["refunds_usd"] for r in rows}
            gaps = {r["region"]: max(0, r["target_usd"] - net[r["region"]]) for r in rows}
            return {"total_net_sales_usd": sum(net.values()),
                    "regions_below_target": sorted(region for region in gaps if gaps[region] > 0),
                    "total_shortfall_usd": sum(gaps.values())}
        if mode == "period_change":
            changes = {r["region"]: (r["current_gross_usd"] - r["current_refunds_usd"])
                       - (r["previous_gross_usd"] - r["previous_refunds_usd"]) for r in rows}
            leader = min(changes, key=lambda region: (-changes[region], region))
            return {"total_net_change_usd": sum(changes.values()), "largest_increase_region": leader,
                    "largest_net_increase_usd": changes[leader]}
        raise ValueError(f"Unknown sales scenario: {mode}")
    if task["subtype"] != "log_investigation":
        raise ValueError("Unsupported multistep subtype")
    events = {}
    for bundle in fixtures.values():
        for event in bundle["events"]:
            if event["event_id"] in events:
                raise ValueError("Duplicate log event ID")
            events[event["event_id"]] = event
    current, chain = task["trace"]["start_event_id"], []
    while current is not None:
        if current in chain:
            raise ValueError("Cycle in causal chain")
        if current not in events:
            raise ValueError(f"Missing cause event: {current}")
        event = events[current]
        if event["request_id"] != task["trace"]["request_id"]:
            raise ValueError("Causal link crosses request IDs")
        chain.append(current)
        current = event["cause_event_id"]
    return {"origin_component": event["component"], "origin_error_code": event["error_code"], "event_chain": chain}


def validate_multistep(task):
    if task["type"] != "multistep" or task["workflow_mode"] != "scripted":
        raise ValueError("Expected a scripted multistep task")
    steps, execution = task["model_steps"], task["execution"]
    if len(steps) != execution["model_calls"] or execution["tool_calls"] != len(steps) - 1:
        raise ValueError("Model/tool counts disagree with the workflow")
    if [s["step"] for s in steps] != list(range(1, len(steps) + 1)) or "tool_after" in steps[-1]:
        raise ValueError("Invalid step numbering or final tool call")
    used = []
    for step in steps[:-1]:
        tool = step["tool_after"]
        key = tool["fixture_key"]
        result = task["tool_fixtures"][key]
        used.append(key)
        args = tool["arguments"]
        if task["subtype"] == "sales_analysis":
            expected_tool = {"net_total": "get_region_sales", "target_gap": "get_region_sales_target",
                             "period_change": "get_region_sales_comparison"}[task["scenario"]]
            if tool["name"] != expected_tool or args["region"] != result["region"]:
                raise ValueError("Sales tool does not match its result")
            for field in ("period",) if task["scenario"] != "period_change" else ("previous_period", "current_period"):
                if args[field] != result[field]:
                    raise ValueError("Sales tool period mismatch")
            for field, value in result.items():
                if field.endswith("_usd") and (type(value) is not int or value < 0):
                    raise ValueError("Fixture amounts must be nonnegative integer dollars")
        elif tool["name"] != "read_log_bundle" or args["bundle"] != result["bundle"] or args["request_id"] != task["trace"]["request_id"]:
            raise ValueError("Log tool does not match its result")
    if len(set(used)) != len(used) or set(used) != set(task["tool_fixtures"]):
        raise ValueError("Each fixture must be revealed once")
    expected = reference_answer(task)
    if task["evaluation"]["expected"] != expected:
        raise ValueError("Reference answer does not match fixture calculations")
    if task["subtype"] == "log_investigation":
        # Every tool contributes at least one event on the required chain.
        chain = set(expected["event_chain"])
        if any(not chain.intersection(e["event_id"] for e in bundle["events"])
               for bundle in task["tool_fixtures"].values()):
            raise ValueError("A tool bundle is unnecessary for this trace")
    if task["generation"] != {"max_tokens": 128, "temperature": 0.0, "ignore_eos": False}:
        raise ValueError("Unexpected generation settings")
    length = task["length"]
    if length["peak_budget_tokens"] > length["context_limit"]:
        raise ValueError("Estimated context budget exceeded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=Path(__file__).parent / "tasks/v1/multistep.jsonl")
    parser.add_argument("--expected-count", type=int, default=20)
    args = parser.parse_args()
    tasks = [json.loads(line) for line in args.tasks.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(tasks) != args.expected_count or len({t["task_id"] for t in tasks}) != len(tasks):
        raise SystemExit("FAIL: unexpected task count or duplicate task IDs")
    for task in tasks:
        try:
            validate_multistep(task)
        except (ValueError, KeyError, TypeError) as exc:
            raise SystemExit(f"FAIL: {task['task_id']}: {exc}") from exc
    print(f"PASS: {len(tasks)} workflows; tool arguments, fixture references, step counts, and derived answers checked.")
    print("No model inference or runtime tool execution performed.")
