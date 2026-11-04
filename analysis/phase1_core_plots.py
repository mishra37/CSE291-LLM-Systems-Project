"""Plot K curves and task-type queueing from phase1_report CSV files.

  python -m analysis.phase1_core_plots --report results/phase1_v2_batch
"""
import argparse
import csv
import statistics
from collections import defaultdict
from pathlib import Path

from analysis.phase1_sweep_report import METRICS, plot, points


def read(path):
    with path.open(newline="", encoding="utf-8") as source:
        return list(csv.DictReader(source))


def core_points(report):
    runs = []
    for raw in read(report / "runs.csv"):
        row = {"factor": int(raw["k"]), "policy": raw["policy"],
               "failed_or_incomplete": int(raw["failed_or_incomplete"]), "offered": int(raw["offered"])}
        row.update({metric: float(raw[metric]) if raw[metric] else None for metric in METRICS})
        runs.append(row)
    return points(runs)


def task_type_queue_plot(report):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    groups = defaultdict(list)
    for raw in read(report / "types.csv"):
        if raw["queue_p95_s"]:
            groups[(raw["type"], raw["policy"], int(raw["k"]))].append(float(raw["queue_p95_s"]))
    fig, ax = plt.subplots(figsize=(8, 5))
    for kind in sorted({key[0] for key in groups}):
        for policy, style in (("fifo_request", "-"), ("fifo_task", "--")):
            data = sorted((k, statistics.median(values)) for (t, p, k), values in groups.items()
                          if t == kind and p == policy)
            if data:
                ax.plot([k for k, _ in data], [v for _, v in data], style, marker="o",
                        label=f"{kind} / {policy}")
    ax.set(xlabel="Scheduler concurrency K", ylabel="Task queue time p95 (s)")
    ax.grid(alpha=0.2)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(report / "task_type_queue_p95.png", dpi=160)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", type=Path, required=True)
    args = ap.parse_args()
    plot(core_points(args.report), "Scheduler concurrency K", args.report)
    task_type_queue_plot(args.report)
    print(f"Core curves written to {args.report}")


if __name__ == "__main__":
    main()
