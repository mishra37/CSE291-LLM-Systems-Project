"""Run paired FIFO baselines on one fixed workload, restarting llama-server for every run.

Run on the GPU host from the repo root. The workload JSONL must already exist.
Example:
  python -m scripts.phase1_fifo --workload workloads/generated/validation_v2_60.jsonl \
      --prefix phase1_v2_batch --k 1 2 4 --repeats 3 --dry-run
Remove --dry-run to execute. Every run has an empty server cache at launch, then
the runner performs the same one-request warm-up before timing begins.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def plan(prefix, ks, repeats, policies):
    if not prefix or not prefix.replace("-", "_").replace("_", "").isalnum():
        raise ValueError("Prefix must contain only letters, numbers, hyphens and underscores")
    if repeats < 1 or not ks or any(k < 1 for k in ks) or len(set(ks)) != len(ks):
        raise ValueError("Provide unique positive K values and at least one repeat")
    return [(f"{prefix}_r{rep}_k{k}_{policy}", rep, k, policy)
            for rep in range(1, repeats + 1) for k in ks for policy in policies]


def run(args):
    workload = Path(args.workload)
    if not workload.is_file():
        raise ValueError(f"Workload missing: {workload}")
    if args.np < max(args.k) or args.ctx < args.np or args.cache_ram < 0:
        raise ValueError("NP must be >= max K; CTX >= NP; cache RAM >= 0")
    if args.arrival == "steady" and args.rate <= 0:
        raise ValueError("Steady arrival rate must be positive")
    if args.tool_delay is not None and args.tool_delay < 0:
        raise ValueError("Tool delay must be nonnegative")
    if args.port < 1 or args.port > 65535:
        raise ValueError("Invalid port")
    runs = plan(args.prefix, args.k, args.repeats, ("fifo_request", "fifo_task"))
    existing = [name for name, *_ in runs if (Path(args.out_dir) / name).exists()]
    if existing:
        raise FileExistsError(f"Run outputs already exist: {', '.join(existing)}")
    digest = sha256(workload)
    for name, rep, k, policy in runs:
        print(f"{name}: fresh server, NP={args.np}, CTX={args.ctx}, cache_ram={args.cache_ram}, "
              f"arrival={args.arrival}, K={k}, workload_sha256={digest}", flush=True)
    if args.dry_run:
        return
    model = Path(args.model).expanduser()
    if not model.is_file():
        raise ValueError(f"Model missing: {model}")
    model_digest = sha256(model)
    revision = subprocess.check_output(["git", "-C", str(Path(args.llama_root).expanduser()), "rev-parse", "HEAD"], text=True).strip()
    source_revision = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    server_flags = f"-c {args.ctx} -np {args.np} --cache-ram {args.cache_ram}"
    env = dict(os.environ, ROOT=str(Path(args.llama_root).expanduser().parent),
               MODEL=str(model), CTX=str(args.ctx), NP=str(args.np), PORT=str(args.port))
    for name, rep, k, policy in runs:
        # The launch script kills the old server on this port and waits until a new one is ready.
        subprocess.run(["bash", "setup/launch_server.sh", "--cache-ram", str(args.cache_ram)],
                       env=env, check=True)
        cmd = [sys.executable, "-m", "runner.run", "--workload", str(workload),
               "--sched", policy, "-k", str(k), "--name", name, "--out-dir", args.out_dir,
               "--arrival", args.arrival, "--rate", str(args.rate), "--sample-ms", str(args.sample_ms),
               "--url", f"http://127.0.0.1:{args.port}", "--server-args", server_flags]
        if args.tool_delay is not None:
            cmd += ["--tool-delay", str(args.tool_delay)]
        subprocess.run(cmd, check=True)
        out = Path(args.out_dir) / name
        (out / "deployment.json").write_text(json.dumps({
            "experiment": args.prefix, "repeat": rep, "policy": policy, "k": k,
            "np": args.np, "ctx": args.ctx, "cache_ram_mib": args.cache_ram,
            "arrival": args.arrival, "rate": args.rate, "tool_delay_override_s": args.tool_delay,
            "workload_sha256": digest, "model_sha256": model_digest,
            "llama_commit": revision, "source_commit": source_revision,
            "cache_procedure": "fresh server for every run; runner's one-request warm-up; timed replay",
            "server_launch": ["bash", "setup/launch_server.sh", "--cache-ram", str(args.cache_ram)],
            "runner_command": cmd,
        }, indent=2) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--workload", required=True)
    ap.add_argument("--prefix", required=True)
    ap.add_argument("--k", type=int, nargs="+", default=[1, 2, 4])
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--np", type=int, default=4)
    ap.add_argument("--ctx", type=int, default=16384)
    ap.add_argument("--cache-ram", type=int, default=0, help="MiB; 0 disables host cache")
    ap.add_argument("--arrival", choices=["batch", "steady"], default="batch")
    ap.add_argument("--rate", type=float, default=1.0)
    ap.add_argument("--tool-delay", type=float)
    ap.add_argument("--sample-ms", type=int, default=100)
    ap.add_argument("--port", type=int, default=8080)
    ap.add_argument("--out-dir", default="results/raw")
    ap.add_argument("--llama-root", default="~/llmsys/llama.cpp")
    ap.add_argument("--model", default="~/llmsys/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf")
    ap.add_argument("--dry-run", action="store_true")
    run(ap.parse_args())


if __name__ == "__main__":
    main()
