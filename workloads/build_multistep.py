"""Build 10 sales and 10 log workflows; no model inference or runtime tools.

python -m workloads.build_multistep --tokenizer /path/to/qwen-tokenizer.json
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import random

from runner.llama_client import chatml
from workloads.generate_long_context import MODEL, REVISION, TOKENIZER_SHA256, TOKENIZER_URL
from workloads.multistep import reference_answer, validate_multistep

SYSTEM = ("Use only tool results revealed so far. This workflow uses a fixed sequence of tools selected by the runner. "
          "On intermediate steps, briefly state current findings and missing information. Do not invent data or issue extra tools. "
          "On the final step, return only the requested JSON object without markdown fences or extra fields.")
REGIONS = ["North", "South", "West", "East", "Central", "Coastal", "Valley"]
SALES_SPECS = [(4, "net_total"), (2, "net_total"), (2, "net_total"), (2, "target_gap"),
               (4, "period_change"), (4, "target_gap"), (4, "period_change"),
               (7, "net_total"), (7, "target_gap"), (7, "period_change")]
LOG_COUNTS = [2, 2, 2, 4, 4, 4, 4, 7, 7, 7]
ORIGINS = [("database", "POOL_EXHAUSTED"), ("cache", "CONNECTION_REFUSED"),
           ("payment", "UPSTREAM_TIMEOUT"), ("auth", "SIGNING_KEY_UNAVAILABLE"),
           ("inventory", "STOCK_LOCK_TIMEOUT"), ("database", "DEADLOCK_DETECTED"),
           ("storage", "QUOTA_EXCEEDED"), ("search", "INDEX_UNAVAILABLE"),
           ("catalog", "CONFIG_MISSING"), ("pricing", "RATE_TABLE_UNAVAILABLE")]


def base(task_id, subtype, scenario, n_tools, seed):
    return {"schema_version": 1, "task_id": task_id, "type": "multistep", "subtype": subtype,
            "scenario": scenario, "workflow_mode": "scripted", "system": SYSTEM,
            "generation": {"max_tokens": 128, "temperature": 0.0, "ignore_eos": False},
            "experiment_defaults": {"tool_delay_s": 2.0, "note": "Added delay per tool; override separately for delay sweeps."},
            "execution": {"model_calls": n_tools + 1, "tool_calls": n_tools, "history_policy": "retain_all",
                          "on_incorrect_intermediate": "continue_and_record", "on_tool_exception": "fail_execution"},
            "source": {"dataset": "llmsys-scripted-agents", "version": "1", "split": "development",
                       "seed": seed, "generator": "workloads/build_multistep.py", "description": "Original fictional fixtures; no generated model replies."}}


def make_steps(task, calls, intermediate):
    steps = []
    for i, call in enumerate(calls, 1):
        steps.append({"step": i, "instruction": "Briefly state the plan and required inputs; no tool results are available yet." if i == 1 else intermediate,
                      "tool_after": call})
    steps.append({"step": len(calls) + 1, "instruction": "All scheduled tool results are now available. Use the complete history and return only the final JSON requested in the initial task."})
    task["model_steps"] = steps


def sales_task(index, n_tools, scenario, preview):
    rng = random.Random(291100 + index)
    task = base(f"multistep-sales-v1-{index:03d}", "sales_analysis", scenario, n_tools, 291100 + index)
    fixtures, calls = {}, []
    for i, region in enumerate(REGIONS[:n_tools]):
        gross, refunds = rng.randrange(100, 901, 10), rng.randrange(0, 101, 5)
        if scenario == "period_change":
            row = {"region": region, "previous_period": "2026-09", "current_period": "2026-10",
                   "previous_gross_usd": gross, "previous_refunds_usd": refunds,
                   "current_gross_usd": gross + rng.randrange(-90, 151, 10), "current_refunds_usd": rng.randrange(0, 101, 5)}
            if index == 10:  # All regions decline; the maximum signed change is still well-defined.
                row.update(previous_gross_usd=500 + 20 * i, previous_refunds_usd=20,
                           current_gross_usd=400 + 10 * i, current_refunds_usd=20)
            name = "get_region_sales_comparison"
            args = {"region": region, "previous_period": "2026-09", "current_period": "2026-10"}
        else:
            row = {"region": region, "period": "2026-10", "gross_sales_usd": gross, "refunds_usd": refunds}
            name = "get_region_sales"
            args = {"region": region, "period": "2026-10"}
            if scenario == "target_gap":
                row["target_usd"] = max(0, gross - refunds + [-50, 0, 75, 120][i % 4])
                if index == 4:
                    row["target_usd"] = gross - refunds + [80, -40][i]
                name = "get_region_sales_target"
        if index == 1:
            row = copy.deepcopy(preview["tool_fixtures"][region])
        elif index == 2:  # Equal net results; explicit tie-break.
            row.update(gross_sales_usd=[250, 300][i], refunds_usd=[50, 100][i])
        elif index == 3:  # Refunds from earlier purchases can exceed this month's gross sales.
            row.update(gross_sales_usd=[50, 80][i], refunds_usd=[100, 100][i])
        elif index == 8 and i == 6:
            row.update(gross_sales_usd=1500, refunds_usd=0)
        fixtures[region] = row
        calls.append({"name": name, "arguments": args, "fixture_key": region})
    task["tool_fixtures"] = fixtures
    task["sales_regions"] = REGIONS[:n_tools]
    regions = ", ".join(task["sales_regions"])
    common = f"Analyze sales for {regions}. All amounts are integer US dollars. Net sales are gross sales minus refunds; refunds can include earlier purchases. "
    if scenario == "net_total":
        instruction = ("For October 2026, calculate combined net sales and identify the largest net-sales region and its net amount. "
                       "If regions tie, choose the alphabetically first region. Return JSON with total_net_sales_usd, largest_region, and largest_region_net_sales_usd.")
    elif scenario == "target_gap":
        instruction = ("For October 2026, calculate total net sales, list regions strictly below their targets in alphabetical order, and sum their shortfalls. "
                       "A region meeting or exceeding its target contributes zero shortfall; surpluses do not offset another region's deficit. "
                       "Return JSON with total_net_sales_usd, regions_below_target, and total_shortfall_usd.")
    else:
        instruction = ("Calculate each region's net change from September to October 2026 (October minus September). "
                       "Report the combined change and the region with the largest signed change, even if all changes are negative. "
                       "Break ties alphabetically. Return JSON with total_net_change_usd, largest_increase_region, and largest_net_increase_usd.")
    task["initial_prompt"] = common + instruction
    make_steps(task, calls, "Update the running calculation using every revealed region. State missing regions. Preserve signed amounts and apply the task's tie/target rules. Do not finalize yet.")
    task["diversity_note"] = {1: "Approved preview data", 2: "Tie for highest net sales", 3: "Negative net sales",
                              4: "Deficit and surplus", 5: "Month-to-month comparison", 6: "Below, at, and above target",
                              7: "Mixed gains and losses", 8: "Winning region arrives last", 9: "Seven-region target accounting",
                              10: "All regions decline"}[index]
    if index == 1:
        task["source"]["derived_from_preview"] = preview["task_id"]
    return task


def log_task(index, n_tools, preview):
    task = base(f"multistep-logs-v1-{index:03d}", "log_investigation", "explicit_cause_chain", n_tools, 291200 + index)
    rng = random.Random(291200 + index)
    request_id = f"req-{800 + index}"
    origin_component, origin_error = ORIGINS[index - 1]
    event_ids = [f"E{index:02d}{i:02d}" for i in range(n_tools)]
    intermediates = ["gateway", "checkout", "router", "worker", "adapter", "client"]
    fixtures, calls = {}, []
    for i in range(n_tools):
        bundle = f"page-{i + 1}"
        event = {"event_id": event_ids[i], "request_id": request_id,
                 "component": intermediates[i] if i < n_tools - 1 else origin_component,
                 "error_code": "UPSTREAM_FAILURE" if i < n_tools - 1 else origin_error,
                 "cause_event_id": event_ids[i + 1] if i < n_tools - 1 else None}
        distractor = {"event_id": f"X{index:02d}{i:02d}", "request_id": f"other-{i}",
                      "component": "database", "error_code": "DEADLOCK_DETECTED", "cause_event_id": None}
        events = [event, distractor]
        if i == 0:  # Same-request unrelated event prevents solving by request ID alone.
            events.append({"event_id": f"N{index:02d}", "request_id": request_id, "component": "metrics",
                           "error_code": "OPTIONAL_TELEMETRY_FAILED", "cause_event_id": None})
        rng.shuffle(events)
        fixtures[bundle] = {"bundle": bundle, "events": events}
        calls.append({"name": "read_log_bundle", "arguments": {"bundle": bundle, "request_id": request_id}, "fixture_key": bundle})
    if index == 1:
        request_id, event_ids = "req-742", ["E-201", "E-202", "D-301"]
        fixtures = copy.deepcopy(preview["tool_fixtures"])
        calls = [copy.deepcopy(s["tool_after"]) for s in preview["model_steps"][:-1]]
        task["source"]["derived_from_preview"] = preview["task_id"]
    task["trace"] = {"request_id": request_id, "start_event_id": event_ids[0]}
    task["tool_fixtures"] = fixtures
    task["initial_prompt"] = (f"Investigate request {request_id}, starting at event {event_ids[0]}. Follow cause_event_id links until an event has no recorded cause. "
                              "Report its component and error code and the ordered event chain from the start to the origin. Ignore events not on that chain, including unrelated events with the same request ID. "
                              "Return only JSON with origin_component, origin_error_code, and event_chain. This is the recorded origin, not a diagnosis of an unobserved deeper cause.")
    task["tool_contract_note"] = "Bundles contain neighboring events, not only events belonging to the requested trace. Follow explicit links."
    task["diversity_note"] = f"{origin_component} origin: {origin_error}; shuffled events and unrelated errors"
    make_steps(task, calls, "Extend the explicit chain from the starting event using revealed bundles. Identify the unresolved cause ID; ignore unrelated events and do not invent missing details.")
    return task


def attach_evaluation_and_length(task, tokenizer):
    expected = reference_answer(task)
    task["evaluation"] = {"method": "structured_json_exact", "expected": expected,
                          "required_types": {k: "integer" if type(v) is int else "array_of_strings" if isinstance(v, list) else "string" for k, v in expected.items()},
                          "extra_fields_allowed": False, "object_key_order_matters": False, "array_order_matters": True,
                          "all_required_fields_must_match": True, "requires_complete_execution": True,
                          "diagnostic_metric": "fraction_of_required_fields_correct"}
    messages, known, budgets = [], [], []
    for i, step in enumerate(task["model_steps"]):
        if i == 0:
            text = task["initial_prompt"] + "\n\n" + step["instruction"]
        else:
            previous = task["model_steps"][i - 1]["tool_after"]
            result = task["tool_fixtures"][previous["fixture_key"]]
            text = f"[tool:{previous['name']}] " + json.dumps(result, separators=(",", ":")) + "\n\n" + step["instruction"]
        messages.append(("user", text))
        n_tokens = len(tokenizer.encode(chatml(task["system"], messages), add_special_tokens=False).ids)
        known.append(n_tokens)
        budgets.append(n_tokens + i * 128 + 128 + 128)
        messages.append(("assistant", ""))
    task["length"] = {"known_prompt_tokens_by_step": known, "budget_tokens_by_step": budgets,
                      "peak_budget_tokens": max(budgets), "context_limit": 4096, "safety_margin_tokens": 128,
                      "method": "Tokenize known history with empty assistant messages; reserve 128 tokens per previous reply, 128 for the current output, and a 128-token margin. Estimate until actual replies exist.",
                      "tokenizer_model": MODEL, "tokenizer_revision": REVISION, "tokenizer_sha256": TOKENIZER_SHA256,
                      "tokenizer_library": "tokenizers==0.22.1", "server_verified": False}
    reference_tokens = len(tokenizer.encode(json.dumps(expected, separators=(",", ":")), add_special_tokens=False).ids)
    task["length"]["reference_answer_tokens"] = reference_tokens
    if reference_tokens > 128:
        raise ValueError("Final reference answer cannot fit output cap")
    validate_multistep(task)


def build(tokenizer):
    preview_path = Path(__file__).parent / "tasks/previews/multistep.jsonl"
    previews = [json.loads(line) for line in preview_path.read_text(encoding="utf-8").splitlines()]
    tasks = [sales_task(i, n, scenario, previews[0]) for i, (n, scenario) in enumerate(SALES_SPECS, 1)]
    tasks += [log_task(i, n, previews[1]) for i, n in enumerate(LOG_COUNTS, 1)]
    for task in tasks:
        attach_evaluation_and_length(task, tokenizer)
    return tasks


def write_outputs(tasks, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "multistep.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks), encoding="utf-8", newline="\n")
    parts = ["# Multistep tasks: 10 sales and 10 log investigations\n",
             f"**Shared system instruction:** {SYSTEM}\n",
             "Each subtype has three tasks with 2 tools, four with 4 tools, and three with 7 tools (3, 5, or 8 model calls). The two approved preview fixtures are retained in task 001 of their subtype.\n",
             "These are scripted workflows: tool order is fixed, but model replies are generated during an eventual run. Histories retain all earlier results and replies. Added tool delay defaults to 2 seconds and can be varied independently.\n",
             "Fixtures and final answers are evaluator/runner data, not initial model input. Reveal only the next tool result after its operation. Incorrect intermediate replies do not cancel scheduled steps; execution errors do. No model or runtime tools have been run for this collection.\n",
             "All outputs have a 128-token cap, temperature 0, and natural EOS. Context budgets reserve space for earlier replies and include a safety margin; they are estimates until actual model responses exist.\n",
             "Parse final JSON and require every expected field and type, no extra fields, and the requested array order; object key order and whitespace do not matter. Completion additionally requires all planned model/tool operations, terminal responses, and no truncation. Track per-field matches separately. Structured runtime scoring is not yet integrated.\n",
             "## Index\n", "| Task | Scenario | Model calls | Tools | Peak token budget estimate |", "|---|---|---:|---:|---:|"]
    for t in tasks:
        parts.append(f"| [{t['task_id']}](#{t['task_id']}) | {t['diversity_note']} | {t['execution']['model_calls']} | {t['execution']['tool_calls']} | {t['length']['peak_budget_tokens']} |")
    for t in tasks:
        parts += [f"\n## {t['task_id']}\n", f"**Task:** {t['initial_prompt']}\n", f"**Variation:** {t['diversity_note']}\n"]
        for step in t["model_steps"]:
            parts += [f"### Model call {step['step']}\n", step["instruction"] + "\n"]
            if "tool_after" in step:
                tool = step["tool_after"]
                parts += [f"**Next tool:** `{tool['name']}` with `{json.dumps(tool['arguments'])}`\n",
                          "**Result after configured delay:**\n", "```json\n" + json.dumps(t["tool_fixtures"][tool["fixture_key"]], indent=2) + "\n```\n"]
        parts += ["**Evaluator-only final answer:**\n", "```json\n" + json.dumps(t["evaluation"]["expected"], indent=2) + "\n```\n"]
    (out / "multistep_review.md").write_text("\n".join(parts), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True, help=TOKENIZER_URL)
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "tasks/v1")
    args = parser.parse_args()
    if hashlib.sha256(args.tokenizer.read_bytes()).hexdigest() != TOKENIZER_SHA256:
        parser.error("Use the pinned Qwen tokenizer")
    from tokenizers import Tokenizer
    tasks = build(Tokenizer.from_file(str(args.tokenizer)))
    write_outputs(tasks, args.out_dir)
    print(f"Wrote {len(tasks)} tasks. Peak context-budget estimates: {[t['length']['peak_budget_tokens'] for t in tasks]}")
