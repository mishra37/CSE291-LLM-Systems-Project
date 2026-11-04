"""Write the fixed 60/80 v2 validation subset and its selection manifest."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path


POSITIONS = {
    "short_qa": list(range(10)),
    "long_context": list(range(10)),
    "long_generation": list(range(10)),
    "sales_analysis": [0, 2, 3, 4, 6, 7, 8, 9],
    "log_investigation": [0, 1, 2, 3, 5, 7, 8, 9],
    "document_lookup": [0, 1, 2, 4, 5, 6, 9],
    "inventory_check": [0, 1, 2, 3, 4, 5, 9],
}


def select(source):
    data = {}
    hashes = {}
    for name in ("short_qa", "long_context", "long_generation", "multistep"):
        path = source / (name + ".jsonl")
        raw = path.read_bytes()
        hashes[path.name] = hashlib.sha256(raw).hexdigest()
        data[name] = [json.loads(line) for line in raw.splitlines() if line.strip()]
    groups = {name: data[name] for name in ("short_qa", "long_context", "long_generation")}
    for subtype in ("sales_analysis", "log_investigation", "document_lookup", "inventory_check"):
        groups[subtype] = [t for t in data["multistep"] if t["subtype"] == subtype]
    chosen = [groups[name][i] for name, positions in POSITIONS.items() for i in positions]
    if len(chosen) != 60 or len({t["task_id"] for t in chosen}) != 60:
        raise ValueError("Selection must contain 60 unique tasks")
    if any(t.get("dataset_version") != "v2" for t in chosen):
        raise ValueError("Expected v2 tasks only")
    raw = "".join(json.dumps(task, ensure_ascii=False, separators=(",", ":")) + "\n" for task in chosen).encode("utf-8")
    manifest = {"dataset_version": "v2", "selection": "60 of 80: all long QA and writing; 10 short QA; 30 balanced multistep",
                "source_file_sha256": hashes, "indices_zero_based": POSITIONS,
                "task_ids": [task["task_id"] for task in chosen], "sha256_jsonl": hashlib.sha256(raw).hexdigest(),
                "counts_by_type": dict(Counter(t["type"] for t in chosen)),
                "counts_by_subtype": dict(Counter(t.get("subtype", "") for t in chosen if t["type"] == "multistep")),
                "planned_model_calls": sum(t["execution"]["model_calls"] for t in chosen),
                "planned_tool_calls": sum(t["execution"]["tool_calls"] for t in chosen)}
    return raw, manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("workloads/tasks/v2"))
    parser.add_argument("--output", type=Path, default=Path("workloads/generated/validation_v2_60.jsonl"))
    parser.add_argument("--manifest", type=Path, default=Path("results/validation_v2_60/selection.json"))
    args = parser.parse_args()
    raw, manifest = select(args.source)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Selected {len(manifest['task_ids'])} tasks; {manifest['planned_model_calls']} model calls; {manifest['planned_tool_calls']} tools; SHA-256 {manifest['sha256_jsonl']}")
