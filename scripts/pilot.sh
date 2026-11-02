#!/usr/bin/env bash
# Small end-to-end pilot on the GPU node: generate a 30-task mixed workload, start
# llama-server with K slots, replay it under both FIFO baselines. ~5-10 min.
# Usage: K=4 CTX=16384 bash scripts/pilot.sh
set -euo pipefail
cd "$(dirname "$0")/.."
K="${K:-4}"
CTX="${CTX:-16384}"
PY="${PY:-$HOME/llmsys/venv/bin/python}"

$PY workloads/generate.py --name pilot --n-tasks 30 --arrival poisson --rate 0.5
CTX=$CTX NP=$K bash setup/launch_server.sh
for SCHED in fifo_request fifo_task; do
  $PY -m runner.run --workload workloads/generated/pilot.jsonl --sched $SCHED -k $K \
      --name "pilot_${SCHED}_k${K}_ctx${CTX}"
done
