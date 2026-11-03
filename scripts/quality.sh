#!/usr/bin/env bash
# Quality check on the fixed v1 collection (80 tasks, natural EOS): replay it under both FIFO
# baselines and both server configs, then score every run. llama-server is restarted before
# every run so no run inherits another run's warm KV/prompt cache.
#   SMOKE=1 bash scripts/quality.sh     5 tasks per type, one config (~2 min) -- run this first
#   K=4 CTX=16384 bash scripts/quality.sh   4 configs + 1 repeat for determinism (~30 min)
set -euo pipefail
cd "$(dirname "$0")/.."
K="${K:-4}"
CTX="${CTX:-16384}"
PY="${PY:-$HOME/llmsys/venv/bin/python}"

run() {  # run <tag> <sched> <workload> <name> <server args...>
  local tag=$1 sched=$2 workload=$3 name=$4; shift 4
  CTX=$CTX NP=$K bash setup/launch_server.sh "$@"
  $PY -m runner.run --workload "workloads/generated/$workload.jsonl" --sched "$sched" -k "$K" \
      --server-args "-c $CTX -np $K $*" --name "$name"
  $PY -m evaluation.score_run --run "results/raw/$name"
}

if [ "${SMOKE:-0}" = 1 ]; then
  $PY -m workloads.export_v1 --name v1_smoke --limit 5 --arrival batch
  run gpuonly fifo_request v1_smoke "v1smoke_gpuonly_fifo_request_k$K" --cache-ram 0
  exit 0
fi

$PY -m workloads.export_v1 --name v1_batch --arrival batch
for TAG in gpuonly ramcache; do
  [ $TAG = gpuonly ] && ARGS="--cache-ram 0" || ARGS="--cache-ram 8192"
  for SCHED in fifo_request fifo_task; do
    # shellcheck disable=SC2086
    run $TAG $SCHED v1_batch "v1_${TAG}_${SCHED}_k$K" $ARGS
  done
done
# repeat one config: same outputs => scheduler comparisons are not confounded by nondeterminism
run gpuonly fifo_request v1_batch "v1_gpuonly_fifo_request_k${K}_rep2" --cache-ram 0
