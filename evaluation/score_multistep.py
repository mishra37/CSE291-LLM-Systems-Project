"""Score saved multistep final answers: structured JSON, exact typed fields.

Rules (from each task's evaluation block): the final response must parse as one JSON object
with exactly the expected keys (no extra or missing fields), the expected types (integers are
not booleans or floats), and equal values (array order matters, key order does not). No
markdown fences or surrounding text are stripped. Execution must be complete, as in score_qa.
"""
import json


def type_ok(value, kind):
    if kind == "integer":
        return type(value) is int
    if kind == "string":
        return isinstance(value, str)
    if kind == "array_of_strings":
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    raise ValueError(f"unknown required type: {kind}")


def check_answer(text, task):
    """Returns (correct, fraction_of_required_fields_correct, error)."""
    ev = task["evaluation"]
    expected, types = ev["expected"], ev["required_types"]
    try:
        answer = json.loads(text.strip())
    except json.JSONDecodeError:
        return 0, 0.0, "not_json"
    if not isinstance(answer, dict):
        return 0, 0.0, "not_object"
    good = sum(1 for k, v in expected.items()
               if k in answer and type_ok(answer[k], types[k]) and answer[k] == v)
    fraction = good / len(expected)
    extra = set(answer) - set(expected)
    if extra and not ev["extra_fields_allowed"]:
        return 0, fraction, "extra_fields"
    if good < len(expected):
        return 0, fraction, "wrong_or_missing_fields"
    return 1, fraction, ""


def aggregate(rows):
    offered, completed = len(rows), sum(r["completed"] for r in rows)
    correct = sum(r["correct"] for r in rows)
    return {"offered": offered, "completed": completed, "correct": correct,
            "missing": sum(r["status"] == "missing" for r in rows),
            "completion_rate": completed / offered if offered else None,
            "accuracy_among_completed": correct / completed if completed else None,
            "success_rate_all_offered": correct / offered if offered else None,
            "mean_field_fraction_all_offered": sum(r["field_fraction"] for r in rows) / offered if offered else None}


def score(tasks, predictions):
    preds = {p["task_id"]: p for p in predictions}
    rows = []
    for task in tasks:
        if task["type"] != "multistep":
            raise ValueError(f"not a multistep task: {task['task_id']}")
        pred = preds.get(task["task_id"])
        completed, correct, fraction, error = False, 0, 0.0, "missing"
        if pred is not None:
            completed = (pred["status"] == "ok" and pred["response_complete"] and not pred["truncated"]
                         and bool(pred["text"].strip()) and pred["steps_done"] == task["execution"]["model_calls"])
            error = "incomplete_execution"
            if completed:
                correct, fraction, error = check_answer(pred["text"], task)
        rows.append({"task_id": task["task_id"], "type": "multistep", "subtype": task["subtype"],
                     "status": pred["status"] if pred else "missing", "completed": completed,
                     "correct": correct, "field_fraction": round(fraction, 4), "error": error,
                     "text": pred["text"] if pred else ""})
    summary = aggregate(rows)
    summary["by_subtype"] = {s: aggregate([r for r in rows if r["subtype"] == s])
                             for s in sorted({r["subtype"] for r in rows})}
    return rows, summary
