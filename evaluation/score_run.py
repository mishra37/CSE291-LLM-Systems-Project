"""Score every task offered in one runner run of the fixed v1 collection.

  python -m evaluation.score_run --run results/raw/<run_name>

Reads the run's config.json to find the workload it replayed and that workload's .meta.json
to find the canonical task files. Scores exactly the offered tasks (missing ones get zero):
  short_qa / long_context  evaluation.score_qa (exact match; F1 for short QA)
  multistep                evaluation.score_multistep (exact typed JSON)
  long_gen                 mechanical checks only (completion, word range, stop reason);
                           rubric quality is judged separately, after the timed run.
Writes <run>/quality/quality_summary.json and quality_tasks.csv.
"""
import argparse
import csv
import json
from pathlib import Path

from evaluation import score_multistep, score_qa


def read_jsonl(path):
    return [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def long_gen_rows(tasks, preds):
    rows = []
    for task in tasks:
        pred = preds.get(task["task_id"])
        completed = bool(pred and pred["status"] == "ok" and pred["response_complete"] and not pred["truncated"]
                         and pred["text"].strip() and pred["steps_done"] == task["execution"]["model_calls"])
        words = len(pred["text"].split()) if pred else 0
        wc = task["evaluation"]["word_count"]
        rows.append({"task_id": task["task_id"], "type": "long_gen", "status": pred["status"] if pred else "missing",
                     "completed": completed, "words": words, "word_range_ok": completed and wc["min"] <= words <= wc["max"],
                     "text": pred["text"] if pred else ""})
    n = len(rows)
    return rows, {"offered": n, "completed": sum(r["completed"] for r in rows),
                  "completion_rate": sum(r["completed"] for r in rows) / n if n else None,
                  "word_range_ok": sum(r["word_range_ok"] for r in rows),
                  "rubric_quality": "not scored (judge after the timed run)"}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", type=Path, required=True)
    ap.add_argument("--workload", type=Path, help="override the workload path recorded in config.json")
    args = ap.parse_args()

    config = json.loads((args.run / "config.json").read_text())
    workload = args.workload or Path(config["args"]["workload"])
    meta = json.loads(workload.with_suffix(".meta.json").read_text())
    if meta.get("source") != "fixed_v1":
        raise SystemExit(f"{workload} is not an export of the fixed v1 collection")
    offered = {r["task_id"] for r in read_jsonl(workload)}
    canonical = [t for path in meta["task_files"].values() for t in read_jsonl(path) if t["task_id"] in offered]
    preds = {p["task_id"]: p for p in read_jsonl(args.run / "predictions.jsonl")}

    summary, rows = {"run": str(args.run), "offered": len(offered)}, []
    qa = [t for t in canonical if t["type"] in ("short_qa", "long_context")]
    if qa:
        ids = {t["task_id"] for t in qa}
        r, s = score_qa.score(qa, [p for p in preds.values() if p["task_id"] in ids])
        rows += r
        summary["qa"] = s
    ms = [t for t in canonical if t["type"] == "multistep"]
    if ms:
        r, s = score_multistep.score(ms, list(preds.values()))
        rows += r
        summary["multistep"] = s
    lg = [t for t in canonical if t["type"] == "long_gen"]
    if lg:
        r, s = long_gen_rows(lg, preds)
        rows += r
        summary["long_gen"] = s

    auto = [r for r in rows if r["type"] != "long_gen"]
    summary["auto_scored"] = {"offered": len(auto), "completed": sum(bool(r["completed"]) for r in auto),
                              "correct": sum(r["correct"] for r in auto)}
    makespan = json.loads((args.run / "summary.json").read_text()).get("makespan_s")
    if makespan:
        summary["correct_tasks_per_s"] = round(summary["auto_scored"]["correct"] / makespan, 4)

    out = args.run / "quality"
    out.mkdir(exist_ok=True)
    (out / "quality_summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(out / "quality_tasks.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    print(json.dumps({k: v for k, v in summary.items() if k != "run"}, indent=2))


if __name__ == "__main__":
    main()
