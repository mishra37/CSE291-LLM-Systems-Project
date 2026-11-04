#!/usr/bin/env bash
# Phase 1 sweeps. Every run restarts llama-server (no warm cache carried over), and runs of the
# fixed v1 collection are scored for quality. A run whose summary.json already exists is
# skipped, so a group can simply be re-run after a dropped SSH session.
#   bash scripts/sweep.sh slots   # slots K = 2,4,8,16 at 4096 KV tokens/slot, v1 batch       (~45 min)
#   bash scripts/sweep.sh delay   # tool delay 0.5, 5, 10 s, v1 batch, K=4                    (~40 min)
#   bash scripts/sweep.sh ctx     # synthetic agents starting from 1k/4k/12k-token documents  (~45 min)
#   bash scripts/sweep.sh kv      # KV memory options at K=8: split vs unified pool, q8_0 KV  (~25 min)
#   bash scripts/sweep.sh rate    # Poisson arrivals 0.25/0.5/1 tasks/s, v1, K=4              (~40 min)
#   bash scripts/sweep.sh micro   # KV restore cost: recompute vs GPU vs SSD (EBS, NVMe) vs RAM (~8 min)
#   REPS=2 bash scripts/sweep.sh slots   # also run a second repeat (_r2) of every config
# Run names: sw_<group>_<value>_<gpuonly|ramcache|...>_<scheduler>[_r<n>]
set -uo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/llmsys/venv/bin/python}"
REPS="${REPS:-1}"
GROUP="${1:?usage: bash scripts/sweep.sh slots|delay|ctx|kv|rate|micro}"

run() {  # run <name> <workload> <sched> <K> <CTX> <score 0|1> [server args...]
  local name=$1 workload=$2 sched=$3 k=$4 ctx=$5 score=$6; shift 6
  for rep in $(seq "$REPS"); do
    local n=$name; [ "$rep" -gt 1 ] && n="${name}_r$rep"
    if [ -f "results/raw/$n/summary.json" ]; then echo "== skip $n (done)"; continue; fi
    echo "== $n"
    CTX=$ctx NP=$k bash setup/launch_server.sh "$@" || { echo "!! server failed to start for $n"; continue; }
    $PY -m runner.run --workload "workloads/generated/$workload.jsonl" --sched "$sched" -k "$k" \
        --server-args "-c $ctx -np $k $*" --name "$n" || { echo "!! run failed: $n"; continue; }
    [ "$score" = 1 ] && $PY -m evaluation.score_run --run "results/raw/$n" >/dev/null
  done
}

GPU="--cache-ram 0"
RAM="--cache-ram 8192"

case $GROUP in
slots)  # more slots = more requests batched together; per-slot KV fixed so every task still fits
  $PY -m workloads.export_v1 --name v1_batch --arrival batch
  for K in 2 4 8 16; do
    for S in fifo_request fifo_task; do
      run "sw_slots_k${K}_gpuonly_$S" v1_batch $S $K $((4096 * K)) 1 $GPU
    done
  done ;;
delay)  # longer tool waits = slots idle longer (fifo_task) / more chance the KV is evicted (fifo_request)
  for D in 0.5 5 10; do
    $PY -m workloads.export_v1 --name "v1_delay$D" --arrival batch --tool-delay $D
    for S in fifo_request fifo_task; do
      run "sw_delay_${D}_gpuonly_$S" "v1_delay$D" $S 4 16384 1 $GPU
    done
  done ;;
ctx)  # bigger agent context = recomputing it after a tool call costs more
  for C in 1000 4000 12000; do
    $PY workloads/generate.py --name "agentdoc$C" --seed 0 --n-tasks 40 --arrival batch \
        --mix multistep=0.5,short_qa=0.5 --doc-tokens $C --steps 5 --tool-delay 2 \
        --tool-tokens 200 --out-tokens 64 --prefix short_shared
    run "sw_ctx_${C}_gpuonly_fifo_request" "agentdoc$C" fifo_request 4 65536 0 $GPU
    run "sw_ctx_${C}_gpuonly_fifo_task"    "agentdoc$C" fifo_task    4 65536 0 $GPU
    run "sw_ctx_${C}_ramcache_fifo_request" "agentdoc$C" fifo_request 4 65536 0 $RAM
  done ;;
kv)  # same 8 slots, different ways to spend KV memory
  $PY -m workloads.export_v1 --name v1_batch --arrival batch
  # 16k tokens split 8 ways = 2k per slot: long documents no longer fit
  run sw_kv_split16k_gpuonly_fifo_request   v1_batch fifo_request 8 16384 1 $GPU
  # same 16k tokens as one shared pool: a slot can use what the others are not using
  run sw_kv_unified16k_gpuonly_fifo_request v1_batch fifo_request 8 16384 1 $GPU --kv-unified
  run sw_kv_unified16k_gpuonly_fifo_task    v1_batch fifo_task    8 16384 1 $GPU --kv-unified
  # 8-bit KV cache: half the memory per token (compare with sw_slots_k8_gpuonly_fifo_request)
  run sw_kv_q8k8_gpuonly_fifo_request       v1_batch fifo_request 8 32768 1 $GPU -ctk q8_0 -ctv q8_0
  ;;
rate)  # slower arrivals = less contention, so fewer evictions and idle slots matter less
  for R in 0.25 0.5 1.0; do
    $PY -m workloads.export_v1 --name "v1_poisson$R" --arrival poisson --rate $R
    for S in fifo_request fifo_task; do
      run "sw_rate_${R}_gpuonly_$S" "v1_poisson$R" $S 4 16384 1 $GPU
    done
  done ;;
micro)  # one slot, 32k tokens: recompute vs keep in GPU vs SSD save/restore vs host-RAM cache
  # SSD twice: EBS (network disk, the default root volume) and the instance's local NVMe
  declare -A DISKS=([ebs]="$HOME/llmsys/slots" [nvme]="/opt/dlami/nvme/slots")
  for D in ebs nvme; do
    DIR=${DISKS[$D]}
    mkdir -p "$DIR" 2>/dev/null || { sudo mkdir -p "$DIR" && sudo chown "$USER" "$DIR"; } || { echo "!! no $DIR"; continue; }
    CTX=32768 NP=1 bash setup/launch_server.sh --cache-ram 0 --slot-save-path "$DIR"
    $PY scripts/kv_microbench.py --mode ssd --out "results/raw/micro_kv/ssd_$D.csv"
    rm -f "$DIR"/micro_*.bin
  done
  CTX=32768 NP=1 bash setup/launch_server.sh --cache-ram 8192
  $PY scripts/kv_microbench.py --mode ram --out results/raw/micro_kv/ram.csv ;;
*) echo "unknown group: $GROUP"; exit 1 ;;
esac
echo "== $GROUP done. Summarize with: $PY -m analysis.summarize"
