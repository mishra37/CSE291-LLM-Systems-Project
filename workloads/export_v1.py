"""Export the fixed v1 task collection into the runner's workload format.

Model inputs are built exactly as the task builders measured them (so recorded token counts
stay valid); evaluation, source, and review metadata are never copied into prompts.
Multistep tasks reveal one tool fixture per step: "[tool:<name>] <compact JSON>" followed by
the next step's instruction, after the tool delay.

  python -m workloads.export_v1 --name v1_batch --arrival batch
  python -m workloads.export_v1 --name v1_poisson --arrival poisson --rate 1.0 --tool-delay 5
  python -m workloads.export_v1 --name v1_smoke --types short_qa,multistep --limit 5

Writes workloads/generated/<name>.jsonl (+ .meta.json). Score a finished run with
  python -m evaluation.score_run --run results/raw/<run_name>
"""
import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

TASK_DIR = Path(__file__).parent / "tasks" / "v1"
FILES = {"short_qa": "short_qa.jsonl", "long_context": "long_context.jsonl",
         "long_gen": "long_generation.jsonl", "multistep": "multistep.jsonl"}


def load_tasks(task_dir, types):
    tasks = []
    for kind in types:
        for line in (task_dir / FILES[kind]).read_text(encoding="utf-8").splitlines():
            if line.strip():
                tasks.append(json.loads(line))
    return tasks


def model_steps(task, tool_delay):
    """Runner steps for one canonical record (model-visible content only)."""
    gen = task["generation"]
    common = {"max_tokens": gen["max_tokens"], "temperature": gen["temperature"], "ignore_eos": gen["ignore_eos"]}
    kind = task["type"]
    if kind == "short_qa":
        return [{"tool_delay_s": 0.0, "user": f"Passage:\n{task['context']}\n\nQuestion: {task['question']}\nAnswer:", **common}]
    if kind == "long_context":
        return [{"tool_delay_s": 0.0, "user": f"Document:\n{task['context']}\n\nQuestion: {task['question']}\nAnswer:", **common}]
    if kind == "long_gen":
        return [{"tool_delay_s": 0.0, "user": task["prompt"], **common}]
    if kind == "multistep":
        delay = tool_delay if tool_delay is not None else task["experiment_defaults"]["tool_delay_s"]
        steps = []
        for i, step in enumerate(task["model_steps"]):
            if i == 0:
                steps.append({"tool_delay_s": 0.0, "user": task["initial_prompt"] + "\n\n" + step["instruction"], **common})
            else:
                tool = task["model_steps"][i - 1]["tool_after"]
                result = task["tool_fixtures"][tool["fixture_key"]]
                text = f"[tool:{tool['name']}] " + json.dumps(result, separators=(",", ":")) + "\n\n" + step["instruction"]
                steps.append({"tool_delay_s": delay, "user": text, "tool": tool["name"], **common})
        return steps
    raise ValueError(f"unknown task type: {kind}")


def peak_context(task, steps):
    """Recorded token budget when the record has one; otherwise a word-based estimate
    (short QA stores no token counts). The runner logs exact counts either way."""
    length = task.get("length", {})
    if "peak_budget_tokens" in length:
        return length["peak_budget_tokens"]
    if "prompt_tokens" in length:
        return length["prompt_tokens"] + task["generation"]["max_tokens"]
    words = len(task["system"].split()) + sum(len(s["user"].split()) for s in steps)
    return int(words * 1.3) + 16 + task["generation"]["max_tokens"]


def arrivals(rng, n, args):
    if args.arrival == "batch":
        return [0.0] * n
    if args.arrival == "steady":
        return [i / args.rate for i in range(n)]
    t, out = 0.0, []
    for _ in range(n):
        out.append(t)
        t += rng.expovariate(args.rate)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--task-dir", default=str(TASK_DIR))
    ap.add_argument("--types", default=",".join(FILES), help="comma-separated subset of " + ",".join(FILES))
    ap.add_argument("--limit", type=int, help="first N tasks per type (smoke tests)")
    ap.add_argument("--arrival", choices=["batch", "steady", "poisson"], default="batch")
    ap.add_argument("--rate", type=float, default=1.0, help="tasks/s for steady and poisson")
    ap.add_argument("--tool-delay", type=float, help="override every multistep tool delay (default: per task, 2 s)")
    ap.add_argument("--seed", type=int, default=0, help="arrival order and times")
    ap.add_argument("--out-dir", default=str(Path(__file__).parent / "generated"))
    args = ap.parse_args()

    task_dir, types = Path(args.task_dir), args.types.split(",")
    canonical = load_tasks(task_dir, types)
    if args.limit:
        canonical = [t for kind in types for t in [c for c in canonical if c["type"] == kind][:args.limit]]

    rng = random.Random(args.seed)
    rng.shuffle(canonical)  # interleave families in arrival order
    times = arrivals(rng, len(canonical), args)
    records = []
    for task, t in zip(canonical, times):
        steps = model_steps(task, args.tool_delay)
        records.append({
            "task_id": task["task_id"], "type": task["type"], "subtype": task.get("subtype"),
            "arrival_s": round(t, 3), "prefix_group": task["type"], "system": task["system"],
            "steps": steps, "est_peak_context": peak_context(task, steps),
        })

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{args.name}.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in records), encoding="utf-8")
    manifest = task_dir / "manifest.json"
    meta = {"source": "fixed_v1", "args": vars(args), "n_tasks": len(records),
            "types": Counter(r["type"] for r in records),
            "model_calls": sum(len(r["steps"]) for r in records),
            "task_files": {k: str(task_dir / FILES[k]) for k in types},
            "manifest_sha256": hashlib.sha256(manifest.read_bytes()).hexdigest() if manifest.exists() else None,
            "duration_s": max(times) if times else 0}
    (out_dir / f"{args.name}.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote {path}: {len(records)} tasks, {meta['model_calls']} model calls, {dict(meta['types'])}")


if __name__ == "__main__":
    main()
