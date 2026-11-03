"""Build 40 workflows across sales, logs, documents, and inventory; no inference.

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
DOCUMENT_MODES = ["section_chain", "effective_revision", "approval_union", "section_chain",
                  "effective_revision", "approval_union", "effective_revision", "section_chain",
                  "effective_revision", "approval_union"]
INVENTORY_MODES = ["sku_shortages", "warehouse_pool", "arrival_cutoff", "sku_shortages",
                  "warehouse_pool", "arrival_cutoff", "sku_shortages", "sku_shortages",
                  "warehouse_pool", "arrival_cutoff"]
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


def document_task(index, n_tools, mode):
    rng = random.Random(291300 + index)
    task = base(f"multistep-documents-v1-{index:03d}", "document_lookup", mode, n_tools, 291300 + index)
    document_id, project = f"manual-{index:02d}", f"Project-{index:02d}"
    fixtures, calls = {}, []
    for i in range(n_tools):
        section_id = f"S{index:02d}{i + 1}"
        if mode == "section_chain":
            next_id = f"S{index:02d}{i + 2}" if i < n_tools - 1 else "END"
            content = (f"This section belongs to the fictional records manual for {project}. Follow its cross-reference for the final storage instructions.\n"
                       f"Project: {project}\nNext section: {next_id}\n")
            if next_id == "END":
                content += f"Owner team: Records-{index:02d}\nRetention days: {30 + 15 * index}\nThis is the terminal section for these instructions."
            else:
                content += "This section does not assign the final owner or retention period."
        elif mode == "effective_revision":
            effective = f"2026-10-{i + 1:02d}" if i < n_tools - 1 else "2026-11-20"
            content = ("This fictional policy excerpt applies only from its effective date. Revision numbers indicate precedence among applicable revisions.\n"
                       f"Policy: backup-{index:02d}\nRevision: {i + 1}\nEffective date: {effective}\n"
                       f"Retention days: {rng.choice([14, 30, 60, 90, 120])}\nOwner team: Team-{rng.choice(['Amber', 'Blue', 'Cedar', 'Delta'])}")
        else:
            required = rng.sample(["finance", "legal", "operations", "security"], 1 + i % 3)
            if index == 3:  # Two sites with overlapping approvals, one requiring security.
                required = [["operations", "security"], ["operations", "legal"]][i]
            if index == 6:  # No security approval anywhere; an empty result list is correct.
                required = [["finance"], ["legal"], ["operations"], ["finance", "legal"]][i]
            content = ("This fictional launch checklist specifies approvals required by this site. Repeated approval names across sites describe the same approval type.\n"
                       f"Site: Site-{index:02d}-{i + 1}\nRequired approvals: {', '.join(required)}\n"
                       "Collect the complete set across every requested site before reporting.")
        fixtures[section_id] = {"document_id": document_id, "section_id": section_id, "content": content}
    order = list(fixtures)
    if mode == "effective_revision":
        rng.shuffle(order)
        if index == 7:
            newest_valid = f"S{index:02d}{n_tools - 1}"
            order.remove(newest_valid)
            order.insert(0, newest_valid)
    calls = [{"name": "read_document_section", "arguments": {"document_id": document_id, "section_id": key}, "fixture_key": key} for key in order]
    task["tool_fixtures"] = fixtures
    if mode == "section_chain":
        task["document_query"] = {"project": project, "start_section": f"S{index:02d}1"}
        task["initial_prompt"] = (f"In fictional manual {document_id}, follow the cross-references for {project}, beginning at section S{index:02d}1. "
                                  "Continue until Next section is END. Report the terminal section's owner team and retention days, plus the ordered section chain from start to end. "
                                  "Return only JSON with owner_team, retention_days (integer), and section_chain.")
        task["diversity_note"] = f"Follow {n_tools} cross-referenced document sections"
    elif mode == "effective_revision":
        task["document_query"] = {"policy": f"backup-{index:02d}", "as_of": "2026-10-31"}
        task["initial_prompt"] = (f"Read the supplied excerpts from fictional manual {document_id} for policy backup-{index:02d}. "
                                  "As of 2026-10-31, select the highest revision number whose effective date is on or before that date; ignore future revisions. "
                                  "Report its revision number, retention days, and owner team as JSON with revision (integer), retention_days (integer), and owner_team. "
                                  "Read all supplied excerpts; tool arrival order does not indicate precedence.")
        task["diversity_note"] = "Ignore future revision; compare applicable revisions in shuffled order" if index != 7 else "Applicable winner is revealed first; later excerpts do not override it"
    else:
        task["document_query"] = {"sites": [f"Site-{index:02d}-{i + 1}" for i in range(n_tools)]}
        task["initial_prompt"] = (f"Combine all site launch checklists supplied from fictional manual {document_id}. "
                                  "List the union of required approval names without duplicates, count those unique names, and list the sites requiring security approval. "
                                  "Sort both lists alphabetically. Return only JSON with required_approvals, approval_count (integer), and sites_requiring_security_review. "
                                  "Use an empty array if no site needs security approval.")
        task["diversity_note"] = "Combine overlapping requirements across sites" if index != 6 else "Union across four checklists; no security-review sites"
    make_steps(task, calls, "Update the document findings from all revealed sections. Apply the specified cross-reference, revision, or set-combination rule. Note missing sections; do not finalize yet.")
    return task


def inventory_task(index, n_tools, mode):
    rng = random.Random(291400 + index)
    task = base(f"multistep-inventory-v1-{index:03d}", "inventory_check", mode, n_tools, 291400 + index)
    fixtures, calls = {}, []
    for i in range(n_tools):
        key = f"WH{index:02d}-{i + 1}" if mode == "warehouse_pool" else f"SKU{index:02d}-{i + 1}"
        on_hand, reserved, damaged = rng.randint(30, 90), rng.randint(0, 10), rng.randint(0, 5)
        row = {"item_id": key, "snapshot": "2026-10-25", "on_hand": on_hand, "reserved": reserved, "damaged": damaged}
        if mode == "warehouse_pool":
            row.update(warehouse=key, sku=f"PART-{index:02d}")
            if index == 2:
                row.update(on_hand=[20, 40][i], reserved=[5, 10][i], damaged=[0, 5][i])
            if index == 5:
                row.update(on_hand=20, reserved=18, damaged=2)
            if index == 9 and i % 2:
                row.update(on_hand=30, reserved=25, damaged=5)
            name = "get_warehouse_inventory"
        else:
            row["demand"] = max(0, on_hand - reserved - damaged + [-5, 0, 15, 25][i % 4])
            if index == 1:
                row.update(on_hand=[10, 20][i], reserved=[2, 5][i], damaged=[1, 0][i], demand=[12, 15][i])
            if index == 4:
                row["demand"] = on_hand - reserved - damaged
                if i == 0:
                    row.update(on_hand=15, reserved=0, damaged=15, demand=0)
            if index == 7:
                row.update(on_hand=20, reserved=5, damaged=0, demand=[30, 30, 15, 10][i])
            if index == 8 and i == n_tools - 1:
                row.update(on_hand=0, reserved=0, damaged=0, demand=100)
            name = "get_item_inventory"
            if mode == "arrival_cutoff":
                row.update(incoming_units=rng.randint(10, 25), arrival_date=["2026-10-29", "2026-10-31", "2026-11-01"][i % 3])
                if index == 3:
                    row.update(on_hand=5, reserved=0, damaged=0, demand=20, incoming_units=15,
                               arrival_date=["2026-10-31", "2026-11-01"][i])
                if index == 6 and i == n_tools - 1:
                    row.update(on_hand=0, reserved=0, damaged=0, demand=30, incoming_units=100, arrival_date="2026-11-01")
                name = "get_inventory_and_arrivals"
        fixtures[key] = row
        calls.append({"name": name, "arguments": {"item_id": key, "snapshot": "2026-10-25"}, "fixture_key": key})
    task["tool_fixtures"] = fixtures
    common = ("Use the fictional inventory snapshots dated 2026-10-25. All quantities are integer units. "
              "Usable stock is on_hand minus reserved minus damaged; reserved and damaged categories do not overlap. "
              "Do not use reserved or damaged stock to meet new demand. ")
    if mode == "warehouse_pool":
        demand = 40 if index == 2 else 50 if index == 5 else 100
        task["inventory_query"] = {"sku": f"PART-{index:02d}", "demand": demand}
        task["initial_prompt"] = common + (f"Pool usable stock of PART-{index:02d} from every supplied warehouse to meet demand of {demand} units. "
                                           "Assume warehouse transfers are unrestricted. Return JSON with available_units, shortfall_units (max of zero and demand minus available), "
                                           "and warehouses_with_stock (alphabetically sorted warehouse IDs with positive usable stock). Use an empty array if none have usable stock.")
    else:
        task["inventory_query"] = {"items": list(fixtures)}
        extra = ""
        if mode == "arrival_cutoff":
            task["inventory_query"]["deadline"] = "2026-10-31"
            extra = ("Add incoming_units to usable stock only when arrival_date is on or before 2026-10-31 (inclusive). "
                     "Incoming units are not yet in on_hand and arrive usable and unreserved. Ignore later shipments. ")
        task["initial_prompt"] = common + extra + ("For each supplied SKU, shortage is max(0, demand minus available usable units). "
                                                    "Stock from one SKU cannot satisfy another SKU's demand. Return JSON with shortage_skus (alphabetically sorted IDs with positive shortage), "
                                                    "total_shortage_units, and largest_shortage_sku. Break largest-shortage ties alphabetically; use an empty string for largest_shortage_sku if there are no shortages.")
    task["diversity_note"] = {1: "One shortage and one exact balance", 2: "Pooled stock exactly meets demand",
                              3: "Arrival on deadline counts; next-day arrival does not", 4: "Zero demand and exact balances; no shortages",
                              5: "All warehouse stock reserved or damaged", 6: "Large late shipment cannot cover a current shortage",
                              7: "Equal largest shortages with alphabetical tie-break", 8: "Worst shortage revealed last",
                              9: "Pool seven warehouses, including zero-usable-stock locations", 10: "Mixed early, on-time, and late arrivals across seven SKUs"}[index]
    make_steps(task, calls, "Update available stock and shortages using all revealed snapshots. Respect reservations, damage, and any arrival cutoff. Keep item identities separate; do not finalize yet.")
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
    tasks += [document_task(i, n, mode) for i, (n, mode) in enumerate(zip(LOG_COUNTS, DOCUMENT_MODES), 1)]
    tasks += [inventory_task(i, n, mode) for i, (n, mode) in enumerate(zip(LOG_COUNTS, INVENTORY_MODES), 1)]
    for task in tasks:
        attach_evaluation_and_length(task, tokenizer)
    return tasks


def write_outputs(tasks, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "multistep.jsonl").write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks), encoding="utf-8", newline="\n")
    parts = ["# Multistep tasks: 40 workflows across four subtypes\n",
             "Ten tasks each cover sales analysis, log investigation, document lookup, and inventory checks.\n",
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
