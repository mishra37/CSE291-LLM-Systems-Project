"""Aggregate and plot one-factor Phase 1 sweeps across paired FIFO runs.

Example:
  python -m analysis.phase1_sweep_report --stem phase1_context_ --vary workload \
      --axis-label 'Initial document tokens (nominal)' --out results/phase1_context
The numeric suffix of each experiment prefix is the factor value. Every factor
must have the same repeat set and both FIFO policies.
"""
import argparse
import csv
import json
import statistics
from collections import defaultdict
from pathlib import Path

from analysis.phase1_report import report_run, write_csv


METRICS = {
    "throughput_completed_tasks_s": "Completed tasks / s",
    "latency_p50_s": "Task latency p50 (s)",
    "latency_p95_s": "Task latency p95 (s)",
    "queue_p95_s": "Task queue time p95 (s)",
    "peak_gpu_mib": "Peak GPU memory (MiB)",
    "peak_server_rss_mib": "Peak server RSS (MiB)",
    "completion_rate": "Task completion rate",
    "generated_tokens_per_s": "Generated tokens / s",
    "context_truncations": "Context truncations",
}


VARIANTS = {"workload": "workload_sha256", "tool_delay": "tool_delay_override_s",
            "rate": "rate", "cache_ram": "cache_ram_mib"}


def collect(raw, stem, scale=1.0, vary="workload"):
    runs, types = [], []
    paths = sorted(p for p in Path(raw).glob(f"{stem}*_r*_k*_fifo_*") if p.is_dir())
    if not paths:
        raise ValueError(f"No runs found for {stem}")
    for path in paths:
        if not (path / "deployment.json").exists() or not (path / "summary.json").exists():
            raise ValueError(f"Incomplete run directory: {path}")
        deployment = json.loads((path / "deployment.json").read_text(encoding="utf-8"))
        experiment = deployment["experiment"]
        if not experiment.startswith(stem):
            raise ValueError(f"Unexpected experiment: {experiment}")
        factor = float(experiment[len(stem):]) * scale
        if vary != "workload" and abs(factor - float(deployment[VARIANTS[vary]])) > 1e-9:
            raise ValueError(f"Factor label does not match {VARIANTS[vary]} in {path}")
        run, by_type = report_run(path)
        runs.append({"factor": factor, **run})
        types.extend({"factor": factor, **row} for row in by_type)
    invariants = ("workload_sha256", "tool_delay_override_s", "rate", "cache_ram_mib",
                  "arrival", "model_sha256", "llama_commit", "source_commit", "np", "ctx", "k", "quality_scope")
    for field in invariants:
        if field == VARIANTS[vary]:
            continue
        if len({r[field] for r in runs}) != 1:
            raise ValueError(f"Sweep mixes {field}")
    pairs = defaultdict(set)
    for run in runs:
        pairs[(run["factor"], run["repeat"])].add(run["policy"])
    for key, policies in pairs.items():
        if policies != {"fifo_request", "fifo_task"}:
            raise ValueError(f"Missing paired policy at {key}")
    repeat_sets = defaultdict(set)
    for factor, repeat in pairs:
        repeat_sets[factor].add(repeat)
    if len({tuple(sorted(repeats)) for repeats in repeat_sets.values()}) != 1:
        raise ValueError("Factor values have different repeat sets")
    return runs, types


def points(runs):
    groups = defaultdict(list)
    for run in runs:
        groups[(run["factor"], run["policy"])].append(run)
    result = []
    for (factor, policy), group in sorted(groups.items()):
        row = {"factor": factor, "policy": policy, "repeats": len(group)}
        for metric in METRICS:
            values = [r[metric] for r in group if r[metric] is not None]
            row[metric + "_median"] = statistics.median(values) if values else None
            row[metric + "_min"] = min(values) if values else None
            row[metric + "_max"] = max(values) if values else None
        row["failure_rate_median"] = statistics.median(r["failed_or_incomplete"] / r["offered"] for r in group)
        result.append(row)
    return result


def plot(rows, axis_label, out):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    for metric, label in {**METRICS, "failure_rate": "Failure / incomplete rate"}.items():
        fig, ax = plt.subplots(figsize=(7, 4.5))
        for policy, color in (("fifo_request", "#1261a0"), ("fifo_task", "#d35400")):
            group = sorted((r for r in rows if r["policy"] == policy), key=lambda r: r["factor"])
            x = [r["factor"] for r in group]
            y = [r[metric + "_median"] for r in group]
            ax.plot(x, y, marker="o", label=policy, color=color)
            if metric != "failure_rate":
                ax.fill_between(x, [r[metric + "_min"] for r in group],
                                [r[metric + "_max"] for r in group], color=color, alpha=0.15)
        ax.set(xlabel=axis_label, ylabel=label)
        ax.grid(alpha=0.2)
        ax.legend()
        fig.tight_layout()
        fig.savefig(out / f"{metric}.png", dpi=160)
        plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--raw", default="results/raw")
    ap.add_argument("--stem", required=True, help="Common experiment prefix before numeric factor value")
    ap.add_argument("--vary", choices=sorted(VARIANTS), required=True)
    ap.add_argument("--scale", type=float, default=1.0, help="Multiply numeric suffix by this value")
    ap.add_argument("--axis-label", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    runs, types = collect(args.raw, args.stem, args.scale, args.vary)
    summary = points(runs)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "runs.csv", runs)
    write_csv(out / "types.csv", types)
    write_csv(out / "points.csv", summary)
    plot(summary, args.axis_label, out)
    print(f"{len(runs)} runs, {len(summary)} policy/factor points; output in {out}")


if __name__ == "__main__":
    main()
