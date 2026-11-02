#!/usr/bin/env bash
# Small end-to-end pilot on the GPU node: generate a 30-task mixed workload, start
# llama-server with K slots, replay it under both FIFO baselines. ~5-10 min per config.
# Usage: K=4 CTX=16384 bash scripts/pilot.sh
# Runs two server configs: GPU-only KV (--cache-ram 0) and llama.cpp's default host-RAM prompt cache.
set -euo pipefail
cd "$(dirname "$0")/.."
K="${K:-4}"
CTX="${CTX:-16384}"
PY="${PY:-$HOME/llmsys/venv/bin/python}"

$PY workloads/generate.py --name pilot --n-tasks 30 --arrival poisson --rate 0.5

declare -A CONFIGS=(
  [gpuonly]="--cache-ram 0"
  [ramcache]="--cache-ram 8192"
)
for TAG in gpuonly ramcache; do
  SERVER_ARGS="${CONFIGS[$TAG]}"
  # shellcheck disable=SC2086
  CTX=$CTX NP=$K bash setup/launch_server.sh $SERVER_ARGS
  for SCHED in fifo_request fifo_task; do
    $PY -m runner.run --workload workloads/generated/pilot.jsonl --sched $SCHED -k $K \
        --server-args "-c $CTX -np $K $SERVER_ARGS" --name "pilot_${TAG}_${SCHED}_k${K}"
  done
done
