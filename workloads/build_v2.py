"""Reproducible prompt/budget revision of v1. References and scoring stay unchanged.

python -m workloads.build_v2 --tokenizer /path/to/qwen-tokenizer.json
"""
import argparse
import copy
import hashlib
import json
from pathlib import Path

from runner.llama_client import chatml
from workloads.generate_long_context import TOKENIZER_SHA256
from workloads.multistep import validate_multistep
from workloads.validate_collection import FILES, inspect


def read(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def digest(record):
    return hashlib.sha256(json.dumps(record, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def revise(original, tokenizer):
    task = copy.deepcopy(original)
    task.update(task_id=original["task_id"].replace("-v1-", "-v2-"), dataset_version="v2",
                revision={"parent_task_id": original["task_id"], "parent_sha256": digest(original),
                          "reason": "Clarify public answer formats and length instructions after the v1 smoke test."})
    if task["type"] == "multistep":
        task["output_types"] = copy.deepcopy(task["evaluation"]["required_types"])
        fields = "\n".join(f"- {key}: {kind}" for key, kind in task["output_types"].items())
        contract = ("Required JSON fields and types (all fields required, no extra fields):\n" + fields +
                    "\nAn array_of_strings is an array of quoted strings, not an array of objects. "
                    "Use the array order specified in the task.")
        if "event_chain" in task["output_types"]:
            contract += " event_chain contains only event ID strings, from the starting event through the origin."
        if "section_chain" in task["output_types"]:
            contract += " section_chain contains only section ID strings, from the starting section through the terminal section."
        task["initial_prompt"] += "\n\n" + contract
        task["model_steps"][-1]["instruction"] = (
            "All scheduled tool results are now available. This is the FINAL ANSWER step. "
            "Recheck the original task against the raw tool results; earlier assistant summaries may contain mistakes. "
            "Do any calculations silently. Return exactly one compact JSON object: start with { and end with }. "
            "Do not output a plan, explanation, Markdown fences, or the field-type descriptions.\n\n" + contract)
        task["model_steps"][-1]["max_tokens"] = 256
        history, known, budgets, previous_caps = [], [], [], 0
        for i, step in enumerate(task["model_steps"]):
            if i == 0:
                user = task["initial_prompt"] + "\n\n" + step["instruction"]
            else:
                tool = task["model_steps"][i - 1]["tool_after"]
                user = f"[tool:{tool['name']}] " + json.dumps(task["tool_fixtures"][tool["fixture_key"]], separators=(",", ":")) + "\n\n" + step["instruction"]
            history.append(("user", user))
            tokens = len(tokenizer.encode(chatml(task["system"], history), add_special_tokens=False).ids)
            cap = step.get("max_tokens", task["generation"]["max_tokens"])
            known.append(tokens)
            budgets.append(tokens + previous_caps + cap + 128)
            history.append(("assistant", ""))
            previous_caps += cap
        task["length"].update(known_prompt_tokens_by_step=known, budget_tokens_by_step=budgets,
                              peak_budget_tokens=max(budgets), server_verified=False,
                              method="Tokenize known ChatML with empty assistant messages; add each prior step's output cap, the current cap, and 128 margin tokens. Intermediate caps 128; final cap 256.")
        validate_multistep(task)
    elif task["type"] == "long_gen":
        words = task["evaluation"]["word_count"]
        target = (words["min"] + words["max"]) // 2
        task["system"] = ("Complete the writing task in English. Meet all content requirements within the stated word range. "
                          "Plan the length before writing and return only the finished response. "
                          "Do not include a preface, an outline, or a word-count note.")
        task["prompt"] += (
            f"\n\nLength requirement: {words['min']}-{words['max']} words TOTAL, including any headings and code. "
            f"Aim for about {target} words, budgeting roughly {target // 4} words per content requirement. "
            "Combine related points and avoid repeating the introduction in a conclusion. "
            "For a story, leave room for the required ending. Before finishing, check the total length and "
            "shorten or develop the response as needed to stay within the range. Return only the finished response.")
        count = len(tokenizer.encode(chatml(task["system"], [("user", task["prompt"])]), add_special_tokens=False).ids)
        task["length"].update(prompt_tokens=count, server_verified=False)
    return task


def review(tasks):
    parts = ["# Revised v2 tasks\n", "Generated from v1 by `workloads/build_v2.py`. Reference answers, fixtures, and scoring rules are unchanged.\n"]
    for t in tasks:
        parts += [f"## {t['task_id']}\n", f"Parent: `{t['revision']['parent_task_id']}`\n",
                  f"**System:** {t['system']}\n"]
        if t["type"] == "multistep":
            parts += [f"**Task:** {t['initial_prompt']}\n",
                      f"**Estimated peak budget:** {t['length']['peak_budget_tokens']} / 4096 tokens, including margin.\n"]
            for step in t["model_steps"]:
                cap = step.get("max_tokens", t["generation"]["max_tokens"])
                parts += [f"### Model call {step['step']} (maximum {cap} tokens)\n", step["instruction"] + "\n"]
                if "tool_after" in step:
                    tool = step["tool_after"]
                    parts += [f"**Next tool:** `{tool['name']}`; arguments: `{json.dumps(tool['arguments'])}`\n",
                              "```json\n" + json.dumps(t["tool_fixtures"][tool["fixture_key"]], indent=2) + "\n```\n"]
        else:
            parts += [t["prompt"] + "\n", f"**Output maximum:** {t['generation']['max_tokens']} tokens; **input:** {t['length']['prompt_tokens']} upstream tokens.\n"]
        parts += ["### Evaluator-only reference / rubric (not sent to the model)\n",
                  "```json\n" + json.dumps(t["evaluation"], indent=2, ensure_ascii=False) + "\n```\n"]
    return "\n".join(parts)


def build(source, destination, tokenizer):
    if source.resolve() == destination.resolve():
        raise ValueError("v1 source must not be overwritten")
    destination.mkdir(parents=True, exist_ok=True)
    for filename in FILES:
        originals = read(source / filename)
        tasks = [revise(t, tokenizer) for t in originals]
        (destination / filename).write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in tasks), encoding="utf-8")
        review_name = filename.replace(".jsonl", "_review.md")
        if filename in ("short_qa.jsonl", "long_context.jsonl"):
            text = (source / review_name).read_text(encoding="utf-8").replace("-v1-", "-v2-")
            text = "QA prompts and references are unchanged from v1; only collection IDs/version metadata differ.\n\n" + text
        else:
            text = review(tasks)
        (destination / review_name).write_text(text, encoding="utf-8")
    manifest = inspect(destination)
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--source", type=Path, default=Path(__file__).parent / "tasks/v1")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "tasks/v2")
    args = parser.parse_args()
    if hashlib.sha256(args.tokenizer.read_bytes()).hexdigest() != TOKENIZER_SHA256:
        parser.error("Use the pinned Qwen tokenizer")
    from tokenizers import Tokenizer
    build(args.source, args.out_dir, Tokenizer.from_file(str(args.tokenizer)))
