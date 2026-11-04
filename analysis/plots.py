"""Phase 1 figures from results/runs_summary.csv and results/raw/micro_kv/.

  python -m analysis.summarize && python -m analysis.plots
Writes results/plots/*.png. One figure per experiment; each panel has its own y-axis.
"""
import re
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

OUT = Path("results/plots")
INK, INK2, GRID, SURFACE = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"
# one colour per serving setup, the same in every figure
SETUPS = {  # label, colour, line style, marker: style + marker keep overlapping lines visible
    "gpuonly_fifo_request": ("give up slot", "#2a78d6", "-", "o"),
    "gpuonly_fifo_task": ("keep slot", "#eb6834", (0, (5, 3)), "s"),
    "ramcache_fifo_request": ("give up slot + 8 GB RAM cache", "#1baf7a", (0, (1.5, 2)), "^"),
    "ram2g_fifo_request": ("give up slot + 2 GB RAM cache", "#eda100", (0, (6, 2, 1.5, 2)), "D"),
}

plt.rcParams.update({
    "figure.facecolor": SURFACE, "axes.facecolor": SURFACE, "savefig.facecolor": SURFACE,
    "axes.edgecolor": GRID, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2,
    "text.color": INK, "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.8,
    "axes.spines.top": False, "axes.spines.right": False, "font.size": 10,
    "axes.titlesize": 11, "axes.titleweight": "bold", "axes.titlelocation": "left",
})


def setup_of(run):
    for key in SETUPS:
        if run.endswith(key) or re.search(f"_{key}_r\\d+$", run):
            return key
    return None


def sweep(df, group, value_re):
    """Rows of one sweep group with numeric x = the swept value."""
    d = df[df.run.str.startswith(f"sw_{group}_")].copy()
    d["x"] = d.run.str.extract(value_re)[0].astype(float)
    d["setup"] = d.run.map(setup_of)
    return d.dropna(subset=["setup"]).sort_values("x")


def end_labels(ax, items, min_gap_px=13):
    """Value labels at line ends, pushed apart vertically so they never overlap."""
    ax.figure.canvas.draw()
    pts = sorted(((ax.transData.transform((x, y))[1], x, y, t) for x, y, t in items), key=lambda p: p[0])
    placed = []
    for py, x, y, t in pts:
        py_new = max(py, placed[-1] + min_gap_px) if placed else py
        placed.append(py_new)
        ax.annotate(t, (x, y), xytext=(6, py_new - py), textcoords="offset points", va="center",
                    fontsize=9, color=INK2)


def lines(ax, d, y, title, ylabel, xlabel, logx=False):
    ends = []
    for key, (label, color, style, marker) in SETUPS.items():
        s = d[d.setup == key]
        if s.empty:
            continue
        ax.plot(s.x, s[y], color=color, lw=2, ls=style, marker=marker, ms=7, label=label,
                markeredgecolor=SURFACE, markeredgewidth=1.5)
        ends.append((s.x.iloc[-1], s[y].iloc[-1], f"{s[y].iloc[-1]:.0f}"))
    if logx:
        ax.set_xscale("log", base=2)
        ax.set_xticks(sorted(d.x.unique()), [f"{v:g}" for v in sorted(d.x.unique())])
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.set_xlabel(xlabel)
    ax.set_ylim(bottom=0)
    end_labels(ax, ends)


def figure(panels, d, name, suptitle, xlabel, logx=False):
    fig, axes = plt.subplots(1, len(panels), figsize=(4.2 * len(panels), 3.6))
    for ax, (y, title, ylabel) in zip(axes, panels):
        lines(ax, d, y, title, ylabel, xlabel, logx)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper right", ncol=len(labels), frameon=False, fontsize=9,
               handlelength=3.5)
    fig.suptitle(suptitle, x=0.01, ha="left", fontsize=12, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.9))
    fig.savefig(OUT / f"{name}.png", dpi=160)
    plt.close(fig)
    print(f"wrote {OUT / name}.png")


def micro():
    ssd = pd.read_csv("results/raw/micro_kv/ssd_nvme.csv").groupby("n_tokens").median(numeric_only=True)
    ram = pd.read_csv("results/raw/micro_kv/ram.csv").groupby("n_tokens").median(numeric_only=True)
    series = [("recompute (KV thrown away)", ssd.recompute_ms, "#2a78d6", "-", "o"),
              ("restore from SSD (llama.cpp slot file)", ssd.ssd_restore_ms, "#eb6834", (0, (5, 3)), "s"),
              ("restore from CPU RAM cache", ram.ram_restore_ms, "#1baf7a", (0, (1.5, 2)), "^"),
              ("KV still in GPU", ssd.gpu_kept_ms, "#eda100", (0, (6, 2, 1.5, 2)), "D")]
    fig, ax = plt.subplots(figsize=(7.5, 4.2))
    for label, s, color, style, marker in series:
        ax.plot(s.index, s / 1000, color=color, lw=2, ls=style, marker=marker, ms=7, label=label,
                markeredgecolor=SURFACE, markeredgewidth=1.5)
    ax.set_xscale("log", base=2)
    ax.set_yscale("log")
    ax.set_xticks(list(ssd.index), [f"{n // 1024}k" if n % 1024 == 0 else f"{n / 1000:.0f}k" for n in ssd.index])
    ax.set_xlabel("conversation length (tokens)")
    ax.set_ylabel("time to resume (s, log scale)")
    ax.set_title("Bringing an agent's KV cache back after a tool call (1 slot, L4)")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    fig.tight_layout()
    end_labels(ax, [(s.index[-1], s.iloc[-1] / 1000, f"{s.iloc[-1] / 1000:.2g} s") for _, s, *_ in series])
    fig.savefig(OUT / "micro_kv_restore.png", dpi=160)
    plt.close(fig)
    print(f"wrote {OUT}/micro_kv_restore.png")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv("results/runs_summary.csv")

    figure([("tok_per_s", "Throughput", "generated tokens / s"),
            ("short_qa_p50_s", "Short QA wait", "median task time (s)"),
            ("multistep_p50_s", "Agent tasks", "median task time (s)"),
            ("peak_gpu_mb", "GPU memory", "peak MB")],
           sweep(df, "slots", r"_k(\d+)_"), "slots",
           "More slots: 80 real tasks, 4,096 KV tokens per slot", "slots (K)", logx=True)

    figure([("makespan_s", "Time to finish all 40 tasks", "seconds"),
            ("prefill_s", "GPU time spent reading prompts", "seconds (summed over requests)"),
            ("peak_rss_mb", "Server CPU RAM", "peak MB")],
           sweep(df, "ctx", r"_ctx_(\d+)_"), "context",
           "Longer agent context: 20 agents + 20 short questions, 4 slots", "agent document (tokens)", logx=True)

    delay = sweep(df, "delay", r"_delay_([\d.]+)_")
    base = df[df.run.isin(["sw_slots_k4_gpuonly_fifo_request", "sw_slots_k4_gpuonly_fifo_task"])].copy()
    base["x"], base["setup"] = 2.0, base.run.map(setup_of)  # default 2 s delay = the K=4 slots run
    delay = pd.concat([delay, base]).sort_values("x")
    figure([("makespan_s", "Time to finish all 80 tasks", "seconds"),
            ("gpu_util_mean", "GPU busy", "mean utilisation (%)"),
            ("short_qa_p50_s", "Short QA wait", "median task time (s)")],
           delay, "tool_delay", "Longer tool waits: 80 real tasks, 4 slots", "tool delay (s)")

    figure([("short_qa_p50_s", "Short QA", "median task time (s)"),
            ("multistep_p50_s", "Agent tasks", "median task time (s)"),
            ("p95_s", "All tasks, tail", "p95 task time (s)")],
           sweep(df, "rate", r"_rate_([\d.]+)_"), "arrival_rate",
           "Busier arrivals: 80 real tasks (Poisson), 4 slots", "arrival rate (tasks / s)")

    if Path("results/raw/micro_kv/ram.csv").exists():
        micro()


if __name__ == "__main__":
    main()
