"""Score saved QA outputs against the full offered task manifest, including missing tasks.

No model calls or judge calls. See evaluation/README.md for the predictions schema.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
from pathlib import Path
import re
import string


def normalize_squad(text):
    text = "".join(char for char in text.lower() if char not in string.punctuation)
    return " ".join(re.sub(r"\b(a|an|the)\b", " ", text).split())


def token_f1(prediction, reference):
    pred, gold = normalize_squad(prediction).split(), normalize_squad(reference).split()
    if not pred or not gold:
        return float(pred == gold)
    common = sum((Counter(pred) & Counter(gold)).values())
    return 2 * common / (len(pred) + len(gold))


def answer_scores(text, task):
    references = [answer["text"] for answer in task["evaluation"]["answers"]]
    if not references:
        raise ValueError(f"{task['task_id']}: no reference answers")
    normalization = task["evaluation"]["normalization"]
    if normalization == "squad_v1":
        return (int(any(normalize_squad(text) == normalize_squad(ref) for ref in references)),
                max(token_f1(text, ref) for ref in references))
    if normalization == "strip_whitespace":
        # Do not collapse distinct identifiers such as WH-123 and WH123.
        return int(any(text.strip() == ref.strip() for ref in references)), None
    raise ValueError(f"Unknown answer normalization: {normalization}")


def aggregate(rows):
    offered = len(rows)
    completed = sum(row["completed"] for row in rows)
    correct = sum(row["correct"] for row in rows)
    f1s = [row["token_f1"] for row in rows if row["token_f1"] is not None]
    return {
        "offered": offered, "completed": completed, "correct": correct,
        "missing": sum(row["status"] == "missing" for row in rows),
        "completion_rate": completed / offered if offered else None,
        "accuracy_among_completed": correct / completed if completed else None,
        "success_rate_all_offered": correct / offered if offered else None,
        "mean_token_f1_all_offered_squad": sum(f1s) / len(f1s) if f1s else None,
    }


def score(tasks, predictions):
    task_map, prediction_map = {}, {}
    for task in tasks:
        task_id = task["task_id"]
        if task_id in task_map:
            raise ValueError(f"Duplicate offered task: {task_id}")
        if task["type"] not in {"short_qa", "long_context"}:
            raise ValueError(f"Unsupported QA task type: {task['type']}")
        # Validate the reference/scoring configuration even when no prediction exists.
        answer_scores("", task)
        task_map[task_id] = task
    if not task_map:
        raise ValueError("No offered tasks")
    for prediction in predictions:
        task_id = prediction["task_id"]
        if task_id not in task_map:
            raise ValueError(f"Prediction is not in the offered manifest: {task_id}")
        if task_id in prediction_map:
            raise ValueError(f"Duplicate prediction: {task_id}; supply one final result per task")
        for flag in ("response_complete", "truncated"):
            if type(prediction[flag]) is not bool:
                raise ValueError(f"{task_id}: {flag} must be a boolean")
        if type(prediction["steps_done"]) is not int or prediction["steps_done"] < 0:
            raise ValueError(f"{task_id}: invalid steps_done")
        if not isinstance(prediction["text"], str) or not isinstance(prediction["status"], str):
            raise ValueError(f"{task_id}: text/status must be strings")
        prediction_map[task_id] = prediction

    rows = []
    for task_id, task in task_map.items():
        pred = prediction_map.get(task_id)
        completed, correct = False, 0
        f1 = 0.0 if task["evaluation"]["normalization"] == "squad_v1" else None
        if pred is not None:
            completed = (pred["status"] == "ok" and pred["response_complete"]
                         and not pred["truncated"] and bool(pred["text"].strip())
                         and pred["steps_done"] == task["execution"]["model_calls"])
            if completed:
                correct, f1 = answer_scores(pred["text"], task)
        rows.append({"task_id": task_id, "type": task["type"],
                     "status": pred["status"] if pred else "missing",
                     "completed": completed, "correct": correct, "token_f1": f1,
                     "text": pred["text"] if pred else ""})
    summary = aggregate(rows)
    summary["by_type"] = {kind: aggregate([row for row in rows if row["type"] == kind])
                          for kind in sorted({row["type"] for row in rows})}
    return rows, summary


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, nargs="+", required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--out-dir", type=Path, required=True)
    parser.add_argument("--makespan-s", type=float, help="Measured experiment duration, excluding offline evaluation")
    args = parser.parse_args()
    if args.makespan_s is not None and not args.makespan_s > 0:
        parser.error("makespan must be positive")
    tasks = [task for path in args.tasks for task in read_jsonl(path)]
    rows, summary = score(tasks, read_jsonl(args.predictions))
    if args.makespan_s is not None:
        summary["correct_tasks_per_s"] = summary["correct"] / args.makespan_s
    summary["inputs"] = [{"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
                         for path in [*args.tasks, args.predictions]]
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "quality_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    with (args.out_dir / "quality_tasks.csv").open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
