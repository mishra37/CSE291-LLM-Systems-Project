#!/usr/bin/env bash
# Sequential unattended launch of the Phase 1 check and all 74 matrix runs.
# Run from a clean repository checkout on the GPU host:
#   PY=$HOME/llmsys/venv/bin/python nohup bash scripts/launch_phase1_all.sh > ~/phase1-launch.log 2>&1 < /dev/null &
set -euo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/llmsys/venv/bin/python}"
WORKLOAD=workloads/generated/validation_v2_60.jsonl

log() { printf '\n== %s %s ==\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"; }
run() { "$PY" -m scripts.phase1_fifo "$@"; }

log "source commit $(git rev-parse HEAD)"
"$PY" -m scripts.select_validation
"$PY" -m workloads.build_phase1_sweeps

log "paired K=2 check"
run --workload "$WORKLOAD" --prefix phase1_check --k 2 --repeats 1 --np 4 --ctx 16384 --cache-ram 0
"$PY" - <<'PY'
import csv
import json
from pathlib import Path

for policy in ("fifo_request", "fifo_task"):
    directory = Path(f"results/raw/phase1_check_r1_k2_{policy}")
    summary = json.loads((directory / "summary.json").read_text())
    if summary["tasks"] != 60 or summary["completed"] != 60 or summary["failed"]:
        raise SystemExit(f"Check run did not complete all 60 tasks: {directory}")
    with (directory / "requests.csv").open(newline="") as source:
        if any(row["truncated"].lower() == "true" for row in csv.DictReader(source)):
            raise SystemExit(f"Context truncation in check run: {directory}")
print("paired check passed: both policies completed 60/60")
PY

log "core concurrency matrix (18 runs)"
run --workload "$WORKLOAD" --prefix phase1_v2_batch --k 1 2 4 --repeats 3 --np 4 --ctx 16384 --cache-ram 0
"$PY" -m analysis.phase1_report --prefix phase1_v2_batch --out results/phase1_v2_batch
"$PY" -m analysis.phase1_core_plots --report results/phase1_v2_batch

log "tool-delay sweep (12 runs)"
for delay in 0 2 8; do
  run --workload "$WORKLOAD" --prefix "phase1_delay_$delay" --k 2 --repeats 2 \
      --np 4 --ctx 16384 --cache-ram 0 --tool-delay "$delay"
done
"$PY" -m analysis.phase1_sweep_report --stem phase1_delay_ --vary tool_delay \
    --axis-label 'Tool delay (s)' --out results/phase1_delay

log "arrival-rate sweep (12 runs)"
for pair in 25:0.25 50:0.5 100:1.0; do
  label=${pair%%:*}; rate=${pair#*:}
  run --workload "$WORKLOAD" --prefix "phase1_rate_$label" --k 2 --repeats 2 \
      --np 4 --ctx 16384 --cache-ram 0 --arrival steady --rate "$rate"
done
"$PY" -m analysis.phase1_sweep_report --stem phase1_rate_ --vary rate --scale 0.01 \
    --axis-label 'Arrival rate (tasks/s)' --out results/phase1_rate

log "context-length sweep (12 runs)"
for tokens in 500 1500 2500; do
  run --workload "workloads/generated/phase1_context_$tokens.jsonl" \
      --prefix "phase1_context_$tokens" --k 2 --repeats 2 --np 4 --ctx 16384 --cache-ram 0
done
"$PY" -m analysis.phase1_sweep_report --stem phase1_context_ --vary workload \
    --axis-label 'Initial document tokens (nominal)' --out results/phase1_context

log "response-length sweep (12 runs)"
for tokens in 32 128 512; do
  run --workload "workloads/generated/phase1_output_$tokens.jsonl" \
      --prefix "phase1_output_$tokens" --k 2 --repeats 2 --np 4 --ctx 16384 --cache-ram 0
done
"$PY" -m analysis.phase1_sweep_report --stem phase1_output_ --vary workload \
    --axis-label 'Requested output tokens' --out results/phase1_output

log "RAM-cache sweep (8 runs)"
for mib in 0 8192; do
  run --workload "$WORKLOAD" --prefix "phase1_cache_$mib" --k 2 --repeats 2 \
      --np 4 --ctx 16384 --cache-ram "$mib"
done
"$PY" -m analysis.phase1_sweep_report --stem phase1_cache_ --vary cache_ram \
    --axis-label 'Host cache budget (MiB)' --out results/phase1_cache

log "all 74 matrix runs complete"
