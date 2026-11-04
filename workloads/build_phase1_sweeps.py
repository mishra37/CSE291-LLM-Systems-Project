"""Build paired synthetic workloads for context- and response-length sweeps.

  python -m workloads.build_phase1_sweeps

Each context variant has the same 40 three-step tasks, tool results, arrivals,
and output caps; only the initial document prefix grows. Each output variant
has the same 40 one-step prompts; only max_tokens changes. Synthetic tasks
measure serving behavior and have no reference-answer score.
"""
import argparse
import json
import random
from pathlib import Path

from workloads import generate


CONTEXT_LEVELS = (500, 1500, 2500)
OUTPUT_LEVELS = (32, 128, 512)
N_TASKS = 40


def estimate(task):
    return (generate.est_tokens(task["system"]) + generate.TURN_OVERHEAD
            + sum(generate.est_tokens(step["user"]) + step["max_tokens"] + 2 * generate.TURN_OVERHEAD
                  for step in task["steps"]))


def base_task(kind, index):
    args = argparse.Namespace(out_tokens=64 if kind == "multistep" else 32,
                              steps=3, tool_delay=2.0, tool_tokens=100, doc_tokens=None,
                              ctx_tokens=None)
    task = generate.make_task(random.Random(10000 + index), kind, args,
                              generate.SHORT_SYSTEM, "short_shared", [])
    task.update(task_id=f"phase1-{kind}-{index:03d}", arrival_s=0.0)
    return task


def build():
    context_base = [base_task("multistep", i) for i in range(N_TASKS)]
    output_base = [base_task("long_gen", i) for i in range(N_TASKS)]
    results = {}
    for level in CONTEXT_LEVELS:
        records = []
        for i, base in enumerate(context_base):
            task = json.loads(json.dumps(base))
            doc = generate.text(random.Random(20000 + i), max(CONTEXT_LEVELS))
            words = doc.split()
            task["steps"][0]["user"] = ("Document:\n" + " ".join(words[:int(level / generate.TOKENS_PER_WORD)])
                                          + "\n\n" + task["steps"][0]["user"])
            task["est_peak_context"] = estimate(task)
            records.append(task)
        results[f"phase1_context_{level}"] = records
    for level in OUTPUT_LEVELS:
        records = []
        for base in output_base:
            task = json.loads(json.dumps(base))
            task["steps"][0]["max_tokens"] = level
            task["est_peak_context"] = estimate(task)
            records.append(task)
        results[f"phase1_output_{level}"] = records
    return results


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out-dir", type=Path, default=Path("workloads/generated"))
    args = ap.parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, records in build().items():
        (args.out_dir / f"{name}.jsonl").write_text(
            "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records), encoding="utf-8")
        print(f"{name}: {len(records)} tasks; estimated maximum context "
              f"{max(r['est_peak_context'] for r in records)} tokens")


if __name__ == "__main__":
    main()
