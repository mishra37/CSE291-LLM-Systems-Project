"""Create 10 deterministic single-call retrieval tasks, with Qwen token counts.

Run from the repo root with the authoring dependencies installed:
  python -m workloads.generate_long_context --tokenizer /path/to/tokenizer.json
The tokenizer must be the pinned Qwen tokenizer identified below. No inference.
"""
import argparse
import hashlib
import json
import random
from pathlib import Path

from runner.llama_client import chatml

MODEL = "Qwen/Qwen2.5-7B-Instruct"
REVISION = "a09a35458c702b33eeacc393d103063234e8bc28"
TOKENIZER_URL = f"https://huggingface.co/{MODEL}/resolve/{REVISION}/tokenizer.json"
TOKENIZER_SHA256 = "c0382117ea329cdf097041132f6d735924b697924d6f6fc3945713e96ce87539"
SYSTEM = ("Answer the question using only the document. Return only the requested "
          "field value exactly as written, with no explanation.")
# A small diagnostic set, not a full factorial experiment. Each document is unique.
SPECS = [
    ("projects", 1800, "beginning"), ("shipments", 2600, "middle"),
    ("equipment", 3400, "end"), ("incidents", 1800, "middle"),
    ("projects", 2600, "end"), ("shipments", 3400, "beginning"),
    ("equipment", 1800, "end"), ("incidents", 2600, "beginning"),
    ("projects", 3400, "middle"), ("shipments", 2600, "middle"),
]


def model_prompt(task):
    user = f"Document:\n{task['context']}\n\nQuestion: {task['question']}\nAnswer:"
    return chatml(task["system"], [("user", user)])


def make_records(kind, rng):
    ids = rng.sample(range(10000, 99999), 200)
    values = rng.sample(range(100000, 999999), 200)
    statuses = ["active", "pending", "complete", "review"]
    rows = []
    for identifier, value in zip(ids, values):
        status, batch = rng.choice(statuses), rng.randint(10, 99)
        if kind == "projects":
            key, answer, field = f"PRJ-{identifier}", str(value), "access code"
            line = f"Project {key} | Access code: {answer} | Status: {status} | Batch: {batch}"
            question = f"What is the access code for project {key}?"
        elif kind == "shipments":
            key, answer, field = f"SH-{identifier}", f"WH-{value}", "destination warehouse"
            line = f"Shipment {key} | Destination warehouse: {answer} | Status: {status} | Batch: {batch}"
            question = f"What is the destination warehouse for shipment {key}?"
        elif kind == "equipment":
            key, answer, field = f"DV-{identifier}", f"RM-{value}", "room"
            line = f"Device {key} | Room: {answer} | Status: {status} | Batch: {batch}"
            question = f"Which room contains device {key}?"
        else:
            key, answer, field = f"IN-{identifier}", f"service-{value}", "responsible service"
            line = f"Incident {key} | Responsible service: {answer} | Status: {status} | Batch: {batch}"
            question = f"Which service is responsible for incident {key}?"
        rows.append({"key": key, "answer": answer, "field": field, "line": line, "question": question})
    return rows


def generate(tokenizer, tokenizer_sha):
    tasks = []
    for index, (kind, target_tokens, position) in enumerate(SPECS, 1):
        seed = 291000 + index
        rows = make_records(kind, random.Random(seed))
        target, distractors = rows[0], rows[1:]
        fraction = {"beginning": 0.1, "middle": 0.5, "end": 0.9}[position]
        for n_rows in range(30, 200):
            target_index = round((n_rows - 1) * fraction)
            selected = distractors[:n_rows - 1]
            selected.insert(target_index, target)
            header = (f"Fictional {kind} register. Each identifier appears once. "
                      "Read the labeled fields to answer the question.\n\n")
            context = header + "\n".join(row["line"] for row in selected)
            task = {"system": SYSTEM, "context": context, "question": target["question"]}
            count = len(tokenizer.encode(model_prompt(task), add_special_tokens=False).ids)
            if count >= target_tokens:
                break
        else:
            raise ValueError("Record pool too small for target token count")
        if count + 32 + 128 > 4096:
            raise ValueError("Prompt + output budget + safety margin exceeds 4096")
        start = context.index(target["answer"])
        if context.count(target["answer"]) != 1 or context.count(target["key"]) != 1:
            raise ValueError("Target or reference value is not unique")
        tasks.append({
            "schema_version": 1, "task_id": f"long_context-v1-{index:03d}",
            "type": "long_context", "answer_type": "identifier", **task,
            "execution": {"model_calls": 1, "tool_calls": 0},
            "generation": {"max_tokens": 32, "temperature": 0.0, "ignore_eos": False},
            "evaluation": {"metrics": ["exact_match"], "normalization": "strip_whitespace",
                           "answers": [{"text": target["answer"], "answer_start": start}]},
            "retrieval": {"template": kind, "target_key": target["key"],
                          "target_field": target["field"], "target_record": target["line"],
                          "record_count": n_rows, "target_record_index": target_index,
                          "target_position": position},
            "length": {"target_prompt_tokens": target_tokens, "prompt_tokens": count,
                       "context_tokens": len(tokenizer.encode(context, add_special_tokens=False).ids),
                       "context_words": len(context.split()), "context_limit": 4096,
                       "reserved_output_tokens": 32, "safety_margin_tokens": 128,
                       "tokenizer_model": MODEL, "tokenizer_revision": REVISION,
                       "tokenizer_sha256": tokenizer_sha, "tokenizer_library": "tokenizers==0.22.1",
                       "server_verified": False},
            "source": {"dataset": "llmsys-synthetic-retrieval", "version": "1",
                       "split": "development", "question_id": f"lookup-{index:03d}",
                       "title": f"Fictional {kind} register {index}", "seed": seed,
                       "generator": "workloads/generate_long_context.py",
                       "description": "Original generated records; RULER-inspired, not an official RULER task."},
        })
    return tasks


def write_outputs(tasks, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / "long_context.jsonl").write_text(
        "".join(json.dumps(task, ensure_ascii=False) + "\n" for task in tasks), encoding="utf-8", newline="\n")
    parts = ["# Long-context QA: 10 synthetic retrieval tasks\n",
             "All records are fictional and generated by a seeded Python script. Each task uses one model call, no tools, and a maximum 32-token answer. Flag issues by task ID.\n",
             "These are RULER-inspired lookup documents, not official RULER benchmark examples. The target appears among similarly formatted distractors.\n",
             "Prompt lengths include the system instruction, entire document, question, and ChatML template. Counts use the pinned upstream Qwen tokenizer; verification against the deployed GGUF server and model inference remain pending.\n",
             f"**System instruction:** {SYSTEM}\n",
             "## Index\n",
             "| Task | Records | Prompt tokens | Target position | Question | Answer |",
             "|---|---:|---:|---|---|---|"]
    for task in tasks:
        r, size = task["retrieval"], task["length"]
        parts.append(f"| [{task['task_id']}](#{task['task_id']}) | {r['record_count']} | {size['prompt_tokens']} | {r['target_position']} | {task['question']} | {task['evaluation']['answers'][0]['text']} |")
    for task in tasks:
        parts.extend([f"\n## {task['task_id']}\n", f"**Question:** {task['question']}\n",
                      f"**Reference answer:** `{task['evaluation']['answers'][0]['text']}`\n",
                      f"**Target record (evaluator only):** `{task['retrieval']['target_record']}`\n",
                      "**Full document sent to the model:**\n", f"```text\n{task['context']}\n```\n"])
    (out / "long_context_review.md").write_text("\n".join(parts), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True, help=f"Download from {TOKENIZER_URL}")
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).parent / "tasks/v1")
    args = parser.parse_args()
    from tokenizers import Tokenizer
    tokenizer_bytes = args.tokenizer.read_bytes()
    tokenizer_sha = hashlib.sha256(tokenizer_bytes).hexdigest()
    if tokenizer_sha != TOKENIZER_SHA256:
        parser.error(f"Unexpected tokenizer file; download the pinned tokenizer: {TOKENIZER_URL}")
    tokenizer = Tokenizer.from_file(str(args.tokenizer))
    tasks = generate(tokenizer, tokenizer_sha)
    write_outputs(tasks, args.out_dir)
    print(f"Wrote {len(tasks)} tasks to {args.out_dir}")
    print("Prompt token counts:", [task["length"]["prompt_tokens"] for task in tasks])
