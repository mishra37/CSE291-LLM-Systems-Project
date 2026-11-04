"""Summarize fixed-task FIFO runs without dropping failed or unjudged tasks.

  python -m analysis.phase1_report --raw results/raw --prefix phase1_v2_batch \
      --out results/phase1_v2_batch

Writes runs.csv, types.csv, and repetitions.csv. Only runs with deployment.json
from scripts.phase1_fifo are included; all must have the same workload/model/runtime.
"""
import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path


def rows(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def percentile(values, percent):
    ordered = sorted(float(x) for x in values)
    if not ordered:
        return None
    rank = (len(ordered) - 1) * percent / 100
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    return round(ordered[low] + (ordered[high] - ordered[low]) * (rank - low), 4)


def max_float(records, key):
    values = [float(r[key]) for r in records if r.get(key) not in (None, "")]
    return max(values) if values else None


def report_run(path):
    deployment = json.loads((path / "deployment.json").read_text(encoding="utf-8"))
    summary = json.loads((path / "summary.json").read_text(encoding="utf-8"))
    offered = jsonl(path / "offered_tasks.jsonl")
    tasks = rows(path / "tasks.csv")
    requests = rows(path / "requests.csv")
    quality = jsonl(path / "quality.jsonl")
    memory = rows(path / "memory.csv")
    ids = [t["task_id"] for t in offered]
    if len(ids) != len(set(ids)) or set(ids) != {t["task_id"] for t in tasks} or set(ids) != {q["task_id"] for q in quality}:
        raise ValueError(f"Task/quality/offered IDs do not match in {path}")
    if len(tasks) != len(ids) or len(quality) != len(ids):
        raise ValueError(f"Duplicate task/quality rows in {path}")
    by_type = defaultdict(list)
    qmap = {q["task_id"]: q for q in quality}
    for task in tasks:
        by_type[task["type"]].append(task)
    base = {"run": path.name, "repeat": deployment["repeat"], "policy": deployment["policy"],
            "k": deployment["k"], "np": deployment["np"], "ctx": deployment["ctx"],
            "cache_ram_mib": deployment["cache_ram_mib"], "arrival": deployment["arrival"],
            "rate": deployment.get("rate"), "tool_delay_override_s": deployment.get("tool_delay_override_s"),
            "workload_sha256": deployment["workload_sha256"], "model_sha256": deployment["model_sha256"],
            "llama_commit": deployment["llama_commit"], "source_commit": deployment.get("source_commit")}
    def metrics(group):
        complete = [t for t in group if qmap[t["task_id"]]["completed"]]
        judged = [qmap[t["task_id"]] for t in group if qmap[t["task_id"]]["correct"] is not None]
        return {"offered": len(group), "completed": len(complete),
                "failed_or_incomplete": len(group) - len(complete),
                "completion_rate": round(len(complete) / len(group), 4) if group else None,
                "latency_p50_s": percentile([t["latency_s"] for t in complete], 50),
                "latency_p95_s": percentile([t["latency_s"] for t in complete], 95),
                "latency_p99_s": percentile([t["latency_s"] for t in complete], 99),
                "queue_p50_s": percentile([t["queue_s"] for t in group], 50),
                "queue_p95_s": percentile([t["queue_s"] for t in group], 95),
                "admit_wait_p95_s": percentile([t["admit_wait_s"] for t in group], 95),
                "correct": sum(q["correct"] is True for q in judged),
                "judged": len(judged),
                "correct_rate_judged": round(sum(q["correct"] is True for q in judged) / len(judged), 4) if judged else None,
                "unjudged": len(group) - len(judged),
                "length_ok": sum(qmap[t["task_id"]]["completed"] and qmap[t["task_id"]].get("length_ok") is True for t in group),
                "task_status_counts": json.dumps({s: sum(t["status"] == s for t in group)
                                                  for s in sorted({t["status"] for t in group})}, sort_keys=True),
                "generated_tokens": sum(int(float(t["gen_tokens"] or 0)) for t in group)}
    whole = metrics(tasks)
    makespan = float(summary["makespan_s"])
    whole.update({"makespan_s": makespan,
                  "throughput_completed_tasks_s": round(whole["completed"] / makespan, 5),
                  "throughput_correct_judged_tasks_s": round(whole["correct"] / makespan, 5),
                  "peak_gpu_mib": max_float(memory, "gpu_mem_mb"),
                  "peak_server_rss_mib": max_float(memory, "server_rss_mb"),
                  "first_gpu_mib": float(memory[0]["gpu_mem_mb"]) if memory and memory[0].get("gpu_mem_mb") else None,
                  "first_server_rss_mib": float(memory[0]["server_rss_mb"]) if memory and memory[0].get("server_rss_mb") else None,
                  "request_queue_p95_s": percentile([r["queue_s"] for r in requests], 95),
                  "model_request_failures": sum(r["status"] != "ok" for r in requests),
                  "output_limit_intermediate": sum(r.get("stop_type") == "limit" and int(r["step"]) < int(r["n_steps"]) - 1 for r in requests),
                  "output_limit_final": sum(r.get("stop_type") == "limit" and int(r["step"]) == int(r["n_steps"]) - 1 for r in requests),
                  "context_truncations": sum(str(r.get("truncated", "")).lower() == "true" for r in requests),
                  "prompt_tokens_computed": sum(int(float(r["prompt_tokens"] or 0)) for r in requests),
                  "prompt_tokens_cached": sum(int(float(r["cached_tokens"] or 0)) for r in requests)})
    type_rows = [{**base, "type": kind, **metrics(group)} for kind, group in sorted(by_type.items())]
    return {**base, **whole}, type_rows


def write_csv(path, data):
    if not data:
        return
    fields = list(dict.fromkeys(key for row in data for key in row))
    with path.open("w", newline="", encoding="utf-8") as sink:
        writer = csv.DictWriter(sink, fields)
        writer.writeheader()
        writer.writerows(data)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default="results/raw")
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    paths = sorted(path for path in Path(args.raw).glob(f"{args.prefix}_r*_k*_fifo_*") if path.is_dir())
    if not paths:
        raise SystemExit("No phase1_fifo runs found")
    for path in paths:
        if not (path / "deployment.json").exists() or not (path / "summary.json").exists():
            raise ValueError(f"Incomplete run directory: {path}")
    run_rows, type_rows = [], []
    for path in paths:
        run, types = report_run(path)
        run_rows.append(run)
        type_rows.extend(types)
    for field in ("workload_sha256", "model_sha256", "llama_commit", "source_commit", "np", "ctx", "cache_ram_mib", "arrival", "rate", "tool_delay_override_s"):
        if len({r[field] for r in run_rows}) != 1:
            raise ValueError(f"Inconsistent {field} across comparison runs")
    pairs = defaultdict(set)
    for row in run_rows:
        pairs[(row["repeat"], row["k"])].add(row["policy"])
    for key, policies in pairs.items():
        if policies != {"fifo_request", "fifo_task"}:
            raise ValueError(f"Missing paired FIFO run for repeat/K {key}: {sorted(policies)}")
    repetitions_by_k = defaultdict(set)
    for repeat, k in pairs:
        repetitions_by_k[k].add(repeat)
    if len({tuple(sorted(repeats)) for repeats in repetitions_by_k.values()}) != 1:
        raise ValueError("K values have different repeat sets")
    groups = defaultdict(list)
    for row in run_rows:
        groups[(row["policy"], row["k"])].append(row)
    repetitions = []
    for (policy, k), group in sorted(groups.items()):
        repetitions.append({"policy": policy, "k": k, "repeats": len(group),
                            **{f"{metric}_median": round(statistics.median(r[metric] for r in group), 4)
                               for metric in ("throughput_completed_tasks_s", "latency_p50_s", "latency_p95_s",
                                              "queue_p95_s", "peak_gpu_mib", "peak_server_rss_mib",
                                              "completion_rate", "correct", "correct_rate_judged")}})
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "runs.csv", run_rows)
    write_csv(out / "types.csv", type_rows)
    write_csv(out / "repetitions.csv", repetitions)
    print(f"{len(run_rows)} runs; reports in {out}")


if __name__ == "__main__":
    main()
