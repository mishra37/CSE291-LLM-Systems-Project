"""Replay a workload against llama-server through a scheduler and record measurements.

Run on the GPU node from the repo root, with llama-server already running (NP >= K):
  python -m runner.run --workload workloads/generated/mixed.jsonl --sched fifo_request -k 4 --name mixed_k4

Writes results/raw/<name>/:
  config.json   run args, server props, workload meta, git commit
  requests.csv  one row per model call (queueing, TTFT, latency, prompt/cached/generated tokens, slot)
  tasks.csv     one row per agent task (completion time split into queue / model / tool time)
  memory.csv    GPU memory + utilization and llama-server RSS, sampled every --sample-ms
  metrics.csv   llama-server /metrics, polled every second
  summary.json  headline numbers (also printed)
"""
import argparse
import asyncio
import csv
import json
import socket
import subprocess
import threading
import time
from pathlib import Path

import numpy as np

from runner.llama_client import LlamaClient, chatml
from scheduler.fifo import SCHEDULERS


class MemorySampler(threading.Thread):
    """Samples GPU memory/util (NVML) and llama-server host RSS in a background thread."""

    def __init__(self, clock, period_s):
        super().__init__(daemon=True)
        self.clock, self.period_s = clock, period_s
        self.rows, self.done = [], threading.Event()

    def run(self):
        try:
            import psutil
            import pynvml
            pynvml.nvmlInit()
            gpu = pynvml.nvmlDeviceGetHandleByIndex(0)
        except Exception as e:  # no GPU (e.g. local testing): skip sampling
            print(f"[memory] sampling disabled: {e}")
            return
        server = next((p for p in psutil.process_iter(["name"]) if p.info["name"] == "llama-server"), None)
        while not self.done.is_set():
            mem = pynvml.nvmlDeviceGetMemoryInfo(gpu)
            util = pynvml.nvmlDeviceGetUtilizationRates(gpu)
            self.rows.append({
                "t": round(self.clock(), 3),
                "gpu_mem_mb": round(mem.used / 2**20, 1),
                "gpu_util": util.gpu,
                "server_rss_mb": round(server.memory_info().rss / 2**20, 1) if server else None,
            })
            self.done.wait(self.period_s)


async def poll_metrics(client, clock, rows, stop):
    while not stop.is_set():
        try:
            rows.append({"t": round(clock(), 3), **await client.metrics()})
        except Exception:
            pass
        await asyncio.sleep(1.0)


async def run_task(task, sched, clock, req_rows, task_rows):
    await asyncio.sleep(max(0.0, task["arrival_s"] - clock()))
    t_arrive = clock()
    status, tool_s, messages = "ok", 0.0, []
    async with sched.task(task) as ticket:
        t_admit = clock()
        for i, step in enumerate(task["steps"]):
            if step["tool_delay_s"] > 0:
                await asyncio.sleep(step["tool_delay_s"])
                tool_s += step["tool_delay_s"]
            messages.append(("user", step["user"]))
            req = {"prompt": chatml(task["system"], messages), "max_tokens": step["max_tokens"]}
            res = await sched.request(req, ticket)
            final, timings = res["final"], res["final"].get("timings", {})
            gen = timings.get("predicted_n", final.get("tokens_predicted", 0))
            req_rows.append({
                "task_id": task["task_id"], "type": task["type"], "step": i, "n_steps": len(task["steps"]),
                "prefix_group": task["prefix_group"], "status": res["status"], "error": res["error"],
                "t_enqueue": round(req["t_enqueue"], 4), "t_dispatch": round(req["t_dispatch"], 4),
                "t_first_token": round(res["t_first_token"], 4) if res["t_first_token"] else None,
                "t_done": round(res["t_done"], 4),
                "queue_s": round(req["t_dispatch"] - req["t_enqueue"], 4),
                "ttft_s": round(res["t_first_token"] - req["t_dispatch"], 4) if res["t_first_token"] else None,
                "latency_s": round(res["t_done"] - req["t_enqueue"], 4),
                "prompt_tokens": timings.get("prompt_n"),   # prompt tokens actually computed
                "cached_tokens": timings.get("cache_n"),    # prompt tokens reused from KV cache
                "gen_tokens": gen, "max_tokens": step["max_tokens"],
                "prefill_ms": timings.get("prompt_ms"), "decode_ms": timings.get("predicted_ms"),
                "slot": final.get("id_slot"), "truncated": final.get("truncated"),
                "stop_type": final.get("stop_type"),
            })
            if res["status"] != "ok":
                status = res["status"]
                break
            messages.append(("assistant", res["text"]))
    t_done = clock()
    mine = [r for r in req_rows if r["task_id"] == task["task_id"]]
    task_rows.append({
        "task_id": task["task_id"], "type": task["type"], "n_steps": len(task["steps"]),
        "steps_done": sum(r["status"] == "ok" for r in mine), "status": status,
        "arrival_s": task["arrival_s"], "t_arrive": round(t_arrive, 4), "t_done": round(t_done, 4),
        "latency_s": round(t_done - t_arrive, 4),
        "admit_wait_s": round(t_admit - t_arrive, 4),
        "queue_s": round(t_admit - t_arrive + sum(r["queue_s"] for r in mine), 4),
        "tool_s": round(tool_s, 4),
        "model_s": round(sum(r["t_done"] - r["t_dispatch"] for r in mine), 4),
        "gen_tokens": sum(r["gen_tokens"] or 0 for r in mine),
        "est_peak_context": task["est_peak_context"],
    })


def pct(xs, q):
    return round(float(np.percentile(xs, q)), 3) if len(xs) else None


def summarize(req_rows, task_rows, mem_rows, makespan):
    ok = [t for t in task_rows if t["status"] == "ok"]
    lat = [t["latency_s"] for t in ok]
    ok_req = [r for r in req_rows if r["status"] == "ok"]
    prompt = sum(r["prompt_tokens"] or 0 for r in ok_req)
    cached = sum(r["cached_tokens"] or 0 for r in ok_req)
    by_type = {}
    for kind in sorted({t["type"] for t in task_rows}):
        ts = [t for t in task_rows if t["type"] == kind]
        l = [t["latency_s"] for t in ts if t["status"] == "ok"]
        by_type[kind] = {"n": len(ts), "completed": len(l), "p50_s": pct(l, 50), "p95_s": pct(l, 95),
                         "queue_p50_s": pct([t["queue_s"] for t in ts], 50)}
    failures = {}
    for t in task_rows:
        if t["status"] != "ok":
            failures[t["status"]] = failures.get(t["status"], 0) + 1
    return {
        "tasks": len(task_rows), "completed": len(ok), "failed": failures,
        "failure_rate": round(1 - len(ok) / max(1, len(task_rows)), 4),
        "task_latency_s": {"p50": pct(lat, 50), "p95": pct(lat, 95), "p99": pct(lat, 99)},
        "request_queue_s": {"p50": pct([r["queue_s"] for r in req_rows], 50),
                            "p95": pct([r["queue_s"] for r in req_rows], 95)},
        "ttft_s": {"p50": pct([r["ttft_s"] for r in ok_req if r["ttft_s"] is not None], 50),
                   "p95": pct([r["ttft_s"] for r in ok_req if r["ttft_s"] is not None], 95)},
        "makespan_s": round(makespan, 2),
        "throughput_tasks_per_s": round(len(ok) / makespan, 4) if makespan else None,
        "throughput_gen_tok_per_s": round(sum(r["gen_tokens"] or 0 for r in ok_req) / makespan, 2) if makespan else None,
        "prefix_cache_hit_ratio": round(cached / max(1, prompt + cached), 4),
        "short_outputs": sum((r["gen_tokens"] or 0) < r["max_tokens"] for r in ok_req),
        "peak_gpu_mem_mb": max((m["gpu_mem_mb"] for m in mem_rows), default=None),
        "peak_server_rss_mb": max((m["server_rss_mb"] or 0 for m in mem_rows), default=None),
        "by_type": by_type,
    }


def write_csv(path, rows):
    if not rows:
        return
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)


async def main(args):
    tasks = [json.loads(l) for l in open(args.workload)]
    if args.max_tasks:
        tasks = tasks[:args.max_tasks]
    out = Path(args.out_dir) / args.name
    out.mkdir(parents=True, exist_ok=True)

    async with LlamaClient(args.url, args.req_timeout) as client:
        props = await client.props()
        n_slots = props.get("total_slots")
        if n_slots is not None and n_slots < args.k:
            print(f"WARNING: server has {n_slots} slots < K={args.k}; extra requests wait inside the server")
        if not args.no_warmup:
            await client.complete(chatml("warmup", [("user", "hi")]), 8)

        t0 = time.monotonic()
        clock = lambda: time.monotonic() - t0
        sched = SCHEDULERS[args.sched](args.k, client, clock)
        await sched.start()
        sampler = MemorySampler(clock, args.sample_ms / 1000)
        sampler.start()
        metric_rows, stop = [], asyncio.Event()
        poller = asyncio.ensure_future(poll_metrics(client, clock, metric_rows, stop))

        req_rows, task_rows = [], []
        await asyncio.gather(*(run_task(t, sched, clock, req_rows, task_rows) for t in tasks))
        makespan = clock()

        stop.set()
        await poller
        await sched.stop()
        sampler.done.set()
        sampler.join()

    meta_path = Path(args.workload).with_suffix(".meta.json")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    config = {
        "args": vars(args), "host": socket.gethostname(), "git_commit": commit,
        "started": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "server": {"total_slots": n_slots, "model_path": props.get("model_path"),
                   "n_ctx": props.get("default_generation_settings", {}).get("n_ctx")},
        "workload_meta": json.loads(meta_path.read_text()) if meta_path.exists() else None,
    }
    summary = summarize(req_rows, task_rows, sampler.rows, makespan)
    (out / "config.json").write_text(json.dumps(config, indent=2))
    (out / "summary.json").write_text(json.dumps(summary, indent=2))
    write_csv(out / "requests.csv", sorted(req_rows, key=lambda r: r["t_enqueue"]))
    write_csv(out / "tasks.csv", sorted(task_rows, key=lambda r: r["t_arrive"]))
    write_csv(out / "memory.csv", sampler.rows)
    write_csv(out / "metrics.csv", metric_rows)
    print(json.dumps(summary, indent=2))
    print(f"results in {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workload", required=True)
    ap.add_argument("--name", required=True, help="run name (output subdirectory)")
    ap.add_argument("--sched", choices=sorted(SCHEDULERS), default="fifo_request")
    ap.add_argument("-k", type=int, default=4, help="fixed concurrency")
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--req-timeout", type=float, default=300)
    ap.add_argument("--max-tasks", type=int, help="only replay the first N tasks (pilots)")
    ap.add_argument("--sample-ms", type=int, default=100)
    ap.add_argument("--no-warmup", action="store_true")
    ap.add_argument("--out-dir", default="results/raw")
    asyncio.run(main(ap.parse_args()))
