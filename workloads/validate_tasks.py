"""Offline structure, rubric, and QA answer-span checks for the fixed task records."""
import argparse
import json
from pathlib import Path


def validate_long_gen(record):
    task_id = record["task_id"]
    if record["schema_version"] != 1 or record["subtype"] not in {"technical_explanation", "story"}:
        raise ValueError(f"{task_id}: invalid long-generation schema/subtype")
    for field in ("system", "prompt", "title"):
        if not isinstance(record[field], str) or not record[field].strip():
            raise ValueError(f"{task_id}: missing {field}")
    if record["execution"] != {"model_calls": 1, "tool_calls": 0}:
        raise ValueError(f"{task_id}: writing task must have one model call and no tools")
    generation = record["generation"]
    if generation["max_tokens"] not in {512, 1024} or generation["temperature"] != 0 or generation["ignore_eos"] is not False:
        raise ValueError(f"{task_id}: invalid generation settings")
    requirements = record["requirements"]
    if len(requirements) != 4 or {r["id"] for r in requirements} != {"r1", "r2", "r3", "r4"}:
        raise ValueError(f"{task_id}: expected four uniquely identified content requirements")
    if any(r["description"] not in record["prompt"] for r in requirements):
        raise ValueError(f"{task_id}: content requirement is not disclosed in the prompt")
    evaluation = record["evaluation"]
    criteria = evaluation["criteria"]
    expected_ids = {"r1", "r2", "r3", "r4", "correctness", "coherence", "development"}
    if evaluation["method"] != "rubric" or len(criteria) != 7 or {c["id"] for c in criteria} != expected_ids:
        raise ValueError(f"{task_id}: incomplete or duplicate rubric criteria")
    if any(c["max_score"] != 2 for c in criteria):
        raise ValueError(f"{task_id}: each criterion must use the 0-2 scale")
    for requirement in requirements:
        criterion = next(c for c in criteria if c["id"] == requirement["id"])
        if criterion.get("requirement_id") != requirement["id"] or criterion["description"] != requirement["description"]:
            raise ValueError(f"{task_id}: rubric does not match its public requirement")
    expected_rule = {"minimum_total": 12, "maximum_total": 14, "minimum_each_criterion": 1,
                     "required_full_score": ["correctness"], "word_range_required": True,
                     "execution_complete_required": True, "critical_failures_allowed": 0}
    if evaluation["pass_rule"] != expected_rule or not evaluation["critical_failures"]:
        raise ValueError(f"{task_id}: incomplete pass/failure rules")
    words = evaluation["word_count"]
    expected_words = (200, 280) if generation["max_tokens"] == 512 else (450, 600)
    if (words["min"], words["max"]) != expected_words or f"{words['min']}-{words['max']} words" not in record["prompt"]:
        raise ValueError(f"{task_id}: inconsistent requested length")
    if words["method"] != "len(text.split())" or not evaluation["reference_notes"]:
        raise ValueError(f"{task_id}: incomplete evaluation specification")
    if record["subtype"] == "technical_explanation" and not evaluation["reference_sources"]:
        raise ValueError(f"{task_id}: missing technical references")
    length = record["length"]
    if not 0 < length["prompt_tokens"] <= 512:
        raise ValueError(f"{task_id}: input is not short")
    if length["reserved_output_tokens"] != generation["max_tokens"]:
        raise ValueError(f"{task_id}: inconsistent output reservation")
    if length["prompt_tokens"] + generation["max_tokens"] + length["safety_margin_tokens"] > length["context_limit"]:
        raise ValueError(f"{task_id}: context budget exceeded")


def validate(path, expected_count=20):
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not records:
        raise ValueError("Task collection is empty")
    if len(records) != expected_count:
        raise ValueError(f"Expected {expected_count} tasks, found {len(records)}")
    ids, source_ids, contexts = set(), set(), set()
    for record in records:
        task_id = record["task_id"]
        if task_id in ids:
            raise ValueError(f"Duplicate task ID: {task_id}")
        ids.add(task_id)
        if record["type"] == "long_gen":
            validate_long_gen(record)
            if record["prompt"] in contexts:
                raise ValueError(f"{task_id}: duplicate writing prompt")
            contexts.add(record["prompt"])
            continue
        if record["schema_version"] != 1 or record["type"] not in {"short_qa", "long_context"}:
            raise ValueError(f"{task_id}: unsupported schema or task type")
        for field in ("system", "context", "question"):
            if not isinstance(record[field], str) or not record[field].strip():
                raise ValueError(f"{task_id}: missing {field}")
        if record["context"] in contexts:
            raise ValueError(f"{task_id}: duplicate passage in QA collection")
        contexts.add(record["context"])
        if record["execution"] != {"model_calls": 1, "tool_calls": 0}:
            raise ValueError(f"{task_id}: QA must have one model call and no tools")
        generation = record["generation"]
        if generation != {"max_tokens": 32, "temperature": 0.0, "ignore_eos": False}:
            raise ValueError(f"{task_id}: unexpected generation settings")
        source = record["source"]
        source_key = (source["dataset"], source["version"], source["split"], source["question_id"])
        if source_key in source_ids:
            raise ValueError(f"{task_id}: duplicate source question")
        source_ids.add(source_key)
        answers = record["evaluation"]["answers"]
        if not answers:
            raise ValueError(f"{task_id}: no reference answers")
        if len({answer["text"] for answer in answers}) != 1:
            raise ValueError(f"{task_id}: conflicting answer texts in this selected collection")
        for answer in answers:
            start, text = answer["answer_start"], answer["text"]
            if not isinstance(start, int) or start < 0 or not isinstance(text, str) or not text:
                raise ValueError(f"{task_id}: invalid answer annotation")
            if record["context"][start:start + len(text)] != text:
                raise ValueError(f"{task_id}: reference answer does not match its passage span")
        if record["type"] == "long_context":
            retrieval, length = record["retrieval"], record["length"]
            context = record["context"]
            rows = context.split("\n\n", 1)[1].splitlines()
            if len(rows) != retrieval["record_count"]:
                raise ValueError(f"{task_id}: record count mismatch")
            if rows[retrieval["target_record_index"]] != retrieval["target_record"]:
                raise ValueError(f"{task_id}: target position mismatch")
            if context.count(retrieval["target_key"]) != 1 or retrieval["target_key"] not in record["question"]:
                raise ValueError(f"{task_id}: nonunique or incorrect lookup key")
            if context.count(answers[0]["text"]) != 1:
                raise ValueError(f"{task_id}: answer value appears more than once")
            fields = dict(part.split(": ", 1) for part in retrieval["target_record"].split(" | ")[1:])
            fields = {key.lower(): value for key, value in fields.items()}
            if fields[retrieval["target_field"]] != answers[0]["text"]:
                raise ValueError(f"{task_id}: reference does not match target field")
            if record["evaluation"]["normalization"] != "strip_whitespace":
                raise ValueError(f"{task_id}: identifier scoring must preserve punctuation and case")
            total = length["prompt_tokens"] + record["generation"]["max_tokens"] + length["safety_margin_tokens"]
            if total > length["context_limit"]:
                raise ValueError(f"{task_id}: recorded token budget exceeds context limit")

    print(f"PASS: {len(records)} records; unique task IDs and inputs; QA spans or writing rubrics validated.")
    print("This validates stored token-budget metadata, not fresh tokenization or deployed-server fit. No inference performed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks", type=Path, default=Path(__file__).parent / "tasks/v1/short_qa.jsonl")
    parser.add_argument("--expected-count", type=int, default=20)
    try:
        args = parser.parse_args()
        validate(args.tasks, args.expected_count)
    except (ValueError, KeyError, TypeError, IndexError, OSError) as exc:
        parser.exit(1, f"FAIL: {exc}\n")
