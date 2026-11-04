"""One row per run: speed, waiting, KV recompute, memory, failures, and (for v1 runs) accuracy.

  python -m analysis.summarize                       # every run in results/raw
  python -m analysis.summarize --match sw_slots      # only runs whose name contains this
Writes results/runs_summary.csv and prints the main columns.

history_recomputed_pct: on later steps of agent tasks, how much of the conversation the model
already had (previous prompt + its previous reply) had to be computed again because its KV
cache was gone. 0% = all reused, 100% = everything re-read. New tokens (the tool result) are
not counted: they always have to be computed.
"""
import argparse
import json
import re
from pathlib import Path

import pandas as pd

TYPES = ["short_qa", "long_context", "long_gen", "multistep"]


def history_recompute(req):
    """Recomputed share of the carried-over conversation on steps after the first."""
    req = req[req.status == "ok"].sort_values(["task_id", "step"])
    redone = carried = 0
    for _, t in req.groupby("task_id"):
        prev = None
        for r in t.itertuples():
            if prev is not None and r.step == prev.step + 1:
                history = prev.prompt_tokens + prev.cached_tokens + prev.gen_tokens
                new = max(0, r.prompt_tokens + r.cached_tokens - history)
                redone += min(history, max(0, r.prompt_tokens - new))
                carried += history
            prev = r
    return 100 * redone / carried if carried else None


def run_row(d):
    cfg = json.loads((d / "config.json").read_text())
    s = json.loads((d / "summary.json").read_text())
    a = cfg["args"]
    ctx = re.search(r"-c (\d+)", a.get("server_args", ""))
    row = {"run": d.name, "sched": a["sched"], "k": a["k"], "ctx": int(ctx.group(1)) if ctx else None,
           "server_args": a.get("server_args", ""), "workload": Path(a["workload"]).stem,
           "tasks": s["tasks"], "completed": s["completed"], "failed": sum(s.get("failed", {}).values()),
           "makespan_s": s["makespan_s"], "tok_per_s": s["throughput_gen_tok_per_s"],
           "tasks_per_s": s["throughput_tasks_per_s"],
           "p50_s": s["task_latency_s"].get("p50"), "p95_s": s["task_latency_s"].get("p95"),
           "peak_gpu_mb": s["peak_gpu_mem_mb"], "peak_rss_mb": s["peak_server_rss_mb"],
           "cache_hit": s["prefix_cache_hit_ratio"]}
    for t in TYPES:
        if t in s.get("by_type", {}):
            row[f"{t}_p50_s"] = s["by_type"][t]["p50_s"]
    req = pd.read_csv(d / "requests.csv")
    ok = req[req.status == "ok"]
    row["gen_tokens"] = int(ok.gen_tokens.sum())
    row["prefill_s"] = round(ok.prefill_ms.sum() / 1000, 1)
    row["history_recomputed_pct"] = history_recompute(req)
    mem = pd.read_csv(d / "memory.csv")
    row["gpu_util_mean"] = round(mem.gpu_util.mean(), 1)
    q = d / "quality" / "quality_summary.json"
    if q.exists():
        qs = json.loads(q.read_text())
        by = qs.get("qa", {}).get("by_type", {})
        for t in ("short_qa", "long_context"):
            if t in by:
                row[f"{t}_correct"] = by[t]["correct"]
        if "multistep" in qs:
            row["multistep_correct"] = qs["multistep"]["correct"]
        if "long_gen" in qs:
            row["long_gen_in_range"] = qs["long_gen"]["word_range_ok"]
        row["correct_tasks_per_s"] = qs.get("correct_tasks_per_s")
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default="results/raw")
    ap.add_argument("--match", default="")
    ap.add_argument("--out", default="results/runs_summary.csv")
    args = ap.parse_args()

    dirs = sorted(d for d in Path(args.raw).iterdir()
                  if (d / "summary.json").exists() and args.match in d.name)
    df = pd.DataFrame([run_row(d) for d in dirs]).round(2)
    if not args.match:
        df.to_csv(args.out, index=False)
        print(f"wrote {args.out} ({len(df)} runs)")
    show = [c for c in ["run", "completed", "failed", "makespan_s", "tok_per_s", "history_recomputed_pct",
                        "short_qa_p50_s", "multistep_p50_s", "peak_gpu_mb", "peak_rss_mb",
                        "multistep_correct"] if c in df]
    with pd.option_context("display.width", 250, "display.max_columns", None, "display.max_rows", None):
        print(df[show].to_string(index=False))


if __name__ == "__main__":
    main()
