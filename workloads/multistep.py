"""Reference calculations and offline validation for scripted multistep tasks.

python -m workloads.multistep --tasks workloads/tasks/v1/multistep.jsonl
This does not execute model requests, agent tools, or a quality evaluator.
"""
import argparse
from datetime import date
import json
from pathlib import Path


def document_fields(section):
    """Extract labeled lines from the fictional document, not hidden metadata."""
    fields = {}
    for line in section["content"].splitlines():
        if ": " in line:
            key, value = line.split(": ", 1)
            if key in fields:
                raise ValueError(f"Repeated document field: {key}")
            fields[key] = value
    return fields


def document_reference(task):
    sections = list(task["tool_fixtures"].values())
    fields = [document_fields(section) for section in sections]
    mode = task["scenario"]
    if mode == "section_chain":
        by_id = {section["section_id"]: document_fields(section) for section in sections}
        if len(by_id) != len(sections):
            raise ValueError("Duplicate document section")
        current, chain = task["document_query"]["start_section"], []
        while current != "END":
            if current in chain or current not in by_id:
                raise ValueError("Cyclic or missing document link")
            field = by_id[current]
            if field["Project"] != task["document_query"]["project"]:
                raise ValueError("Document link crosses projects")
            chain.append(current)
            current = field["Next section"]
        return {"owner_team": field["Owner team"], "retention_days": int(field["Retention days"]), "section_chain": chain}
    if mode == "effective_revision":
        cutoff = date.fromisoformat(task["document_query"]["as_of"])
        applicable = [field for field in fields if field["Policy"] == task["document_query"]["policy"]
                      and date.fromisoformat(field["Effective date"]) <= cutoff]
        if not applicable:
            raise ValueError("No effective policy revision")
        revisions = [int(field["Revision"]) for field in applicable]
        if len(revisions) != len(set(revisions)):
            raise ValueError("Duplicate applicable revision")
        latest = max(applicable, key=lambda f: int(f["Revision"]))
        return {"revision": int(latest["Revision"]), "retention_days": int(latest["Retention days"]), "owner_team": latest["Owner team"]}
    if mode == "approval_union":
        approvals = {field["Site"]: set(field["Required approvals"].split(", ")) for field in fields}
        if len(approvals) != len(fields):
            raise ValueError("Duplicate site document")
        combined = set().union(*approvals.values())
        return {"required_approvals": sorted(combined), "approval_count": len(combined),
                "sites_requiring_security_review": sorted(site for site, required in approvals.items() if "security" in required)}
    raise ValueError(f"Unknown document scenario: {mode}")


def inventory_reference(task):
    rows = list(task["tool_fixtures"].values())
    available = {row["item_id"]: max(0, row["on_hand"] - row["reserved"] - row["damaged"]) for row in rows}
    if len(available) != len(rows):
        raise ValueError("Duplicate inventory item")
    if task["scenario"] == "warehouse_pool":
        if len({row["warehouse"] for row in rows}) != len(rows) or any(row["sku"] != task["inventory_query"]["sku"] for row in rows):
            raise ValueError("Warehouse records must be distinct and refer to the requested SKU")
        total = sum(available.values())
        return {"available_units": total, "shortfall_units": max(0, task["inventory_query"]["demand"] - total),
                "warehouses_with_stock": sorted(row["warehouse"] for row in rows if available[row["item_id"]] > 0)}
    if task["scenario"] == "arrival_cutoff":
        cutoff = date.fromisoformat(task["inventory_query"]["deadline"])
        for row in rows:
            if date.fromisoformat(row["arrival_date"]) <= cutoff:
                available[row["item_id"]] += row["incoming_units"]
    elif task["scenario"] != "sku_shortages":
        raise ValueError("Unknown inventory scenario")
    shortfalls = {row["item_id"]: max(0, row["demand"] - available[row["item_id"]]) for row in rows}
    affected = sorted(sku for sku, units in shortfalls.items() if units > 0)
    worst = min(affected, key=lambda sku: (-shortfalls[sku], sku)) if affected else ""
    return {"shortage_skus": affected, "total_shortage_units": sum(shortfalls.values()), "largest_shortage_sku": worst}


def reference_answer(task):
    fixtures = task["tool_fixtures"]
    mode = task["scenario"]
    if task["subtype"] == "document_lookup":
        return document_reference(task)
    if task["subtype"] == "inventory_check":
        return inventory_reference(task)
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
        elif task["subtype"] == "log_investigation":
            if tool["name"] != "read_log_bundle" or args["bundle"] != result["bundle"] or args["request_id"] != task["trace"]["request_id"]:
                raise ValueError("Log tool does not match its result")
        elif task["subtype"] == "document_lookup":
            if tool["name"] != "read_document_section" or args["document_id"] != result["document_id"] or args["section_id"] != result["section_id"]:
                raise ValueError("Document tool does not match its section")
            if not isinstance(result["content"], str) or not result["content"].strip():
                raise ValueError("Empty document section")
        elif task["subtype"] == "inventory_check":
            expected_tool = {"sku_shortages": "get_item_inventory", "warehouse_pool": "get_warehouse_inventory",
                             "arrival_cutoff": "get_inventory_and_arrivals"}[task["scenario"]]
            if tool["name"] != expected_tool or args["item_id"] != result["item_id"] or args["snapshot"] != result["snapshot"]:
                raise ValueError("Inventory tool does not match its result")
            for field in ("on_hand", "reserved", "damaged", "demand", "incoming_units"):
                if field in result and (type(result[field]) is not int or result[field] < 0):
                    raise ValueError("Inventory quantities must be nonnegative integers")
            if result["reserved"] + result["damaged"] > result["on_hand"]:
                raise ValueError("Reserved and damaged stock exceed on-hand stock")
        else:
            raise ValueError("Unknown multistep subtype")
    if len(set(used)) != len(used) or set(used) != set(task["tool_fixtures"]):
        raise ValueError("Each fixture must be revealed once")
    expected = reference_answer(task)
    if task["evaluation"]["expected"] != expected:
        raise ValueError("Reference answer does not match fixture calculations")
    if task["subtype"] == "document_lookup" and task["scenario"] == "section_chain":
        if set(expected["section_chain"]) != {row["section_id"] for row in task["tool_fixtures"].values()}:
            raise ValueError("Section chain does not use every document tool result")
    if task["subtype"] == "log_investigation":
        # Every tool contributes at least one event on the required chain.
        chain = set(expected["event_chain"])
        if any(not chain.intersection(e["event_id"] for e in bundle["events"])
               for bundle in task["tool_fixtures"].values()):
            raise ValueError("A tool bundle is unnecessary for this trace")
    if task["generation"] != {"max_tokens": 128, "temperature": 0.0, "ignore_eos": False}:
        raise ValueError("Unexpected generation settings")
    caps = [step.get("max_tokens", task["generation"]["max_tokens"]) for step in steps]
    if any(type(cap) is not int or cap not in (128, 256) for cap in caps):
        raise ValueError("Invalid step output budget")
    if any(cap != 128 for cap in caps[:-1]):
        raise ValueError("Intermediate steps must retain the 128-token cap")
    if task.get("dataset_version") == "v2":
        if task["output_types"] != task["evaluation"]["required_types"] or caps[-1] != 256:
            raise ValueError("Public answer types or final output budget mismatch")
        for field, kind in task["output_types"].items():
            declaration = f"- {field}: {kind}"
            if declaration not in task["initial_prompt"] or declaration not in steps[-1]["instruction"]:
                raise ValueError("Answer field type must be public at the initial and final step")
    length = task["length"]
    known = length["known_prompt_tokens_by_step"]
    budgets = [n + sum(caps[:i]) + caps[i] + length["safety_margin_tokens"] for i, n in enumerate(known)]
    if len(known) != len(steps) or length["budget_tokens_by_step"] != budgets or length["peak_budget_tokens"] != max(budgets):
        raise ValueError("Context budget does not match per-step output allowances")
    if length.get("reference_answer_tokens", 0) > caps[-1]:
        raise ValueError("Reference JSON exceeds final output budget")
    if length["peak_budget_tokens"] > length["context_limit"]:
        raise ValueError("Estimated context budget exceeded")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=Path(__file__).parent / "tasks/v1/multistep.jsonl")
    parser.add_argument("--expected-count", type=int, default=40)
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
