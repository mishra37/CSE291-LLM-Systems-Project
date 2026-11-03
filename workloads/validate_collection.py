"""Validate all 80 task definitions and optionally refresh their draft manifest.

python -m workloads.validate_collection --write-manifest
Hashes canonical JSON records, so Git line-ending conversions do not change them.
No inference, runtime tools, or model quality measurements.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from workloads.multistep import validate_multistep
from workloads.validate_tasks import validate

FILES = {"short_qa.jsonl": 20, "long_context.jsonl": 10, "long_generation.jsonl": 10, "multistep.jsonl": 40}


def inspect(root):
    all_tasks, entries = [], []
    for filename, expected in FILES.items():
        path = root / filename
        records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
        if len(records) != expected:
            raise ValueError(f"{filename}: expected {expected} records")
        if filename == "multistep.jsonl":
            for record in records:
                validate_multistep(record)
            subtypes = Counter(t["subtype"] for t in records)
            if subtypes != {"sales_analysis": 10, "log_investigation": 10, "document_lookup": 10, "inventory_check": 10}:
                raise ValueError("Unexpected multistep subtype distribution")
            for subtype in subtypes:
                if Counter(t["execution"]["tool_calls"] for t in records if t["subtype"] == subtype) != {2: 3, 4: 4, 7: 3}:
                    raise ValueError(f"{subtype}: incorrect tool-count distribution")
        else:
            validate(path, expected)
        canonical = "".join(json.dumps(record, sort_keys=True, ensure_ascii=False, separators=(",", ":")) + "\n" for record in records)
        entries.append({"path": filename, "tasks": expected, "sha256_canonical_jsonl": hashlib.sha256(canonical.encode("utf-8")).hexdigest()})
        all_tasks.extend(records)
    if len({t["task_id"] for t in all_tasks}) != 80:
        raise ValueError("Duplicate task ID across collections")
    return {"schema_version": 1, "dataset_version": "v1", "status": "draft_development",
            "total_tasks": 80, "task_types": dict(sorted(Counter(t["type"] for t in all_tasks).items())),
            "planned_model_calls": sum(t["execution"]["model_calls"] for t in all_tasks),
            "planned_tool_calls": sum(t["execution"]["tool_calls"] for t in all_tasks),
            "checksum_method": "UTF-8 JSON per record, sort_keys=True, ensure_ascii=False, separators=(',', ':'), LF after each record; original record order retained.",
            "files": entries,
            "measurement_status": "Task definitions validated offline. No inference results; runtime integration and deployed-server checks pending."}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tasks-dir", type=Path, default=Path(__file__).parent / "tasks/v1")
    parser.add_argument("--write-manifest", action="store_true")
    args = parser.parse_args()
    manifest = inspect(args.tasks_dir)
    path = args.tasks_dir / "manifest.json"
    if args.write_manifest:
        path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    elif not path.exists() or json.loads(path.read_text(encoding="utf-8")) != manifest:
        raise SystemExit("FAIL: missing/stale manifest. Review task changes, then use --write-manifest.")
    print(f"PASS: {manifest['total_tasks']} unique tasks; {manifest['planned_model_calls']} planned model calls; {manifest['planned_tool_calls']} planned tool calls; manifest matches.")
