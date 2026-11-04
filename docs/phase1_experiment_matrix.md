# Phase 1 experiment matrix and figures

Use the same pinned Qwen2.5-7B-Instruct Q4_K_M model and llama.cpp revision for
every comparison. [The run protocol](phase1_protocol.md) defines completion,
quality, and timing. This matrix extends the 60-task baseline with controlled
one-factor sweeps. It is a launch plan; no result is implied until its raw run
directory exists.

| Group | Vary | Fixed within group | Tasks | New runs | Main figure |
|---|---|---|---:|---:|---|
| Core FIFO | K=1,2,4 and two policies; 3 repeats | NP=4, CTX=16384, batch, 2 s tools, RAM cache 0 | Same 60 v2 tasks | 18 | K vs completed tasks/s, p95 latency, queue p95, peak memory, failure rate |
| Tool delay | 0,2,8 s; two policies; 2 repeats | K=2, NP=4, same 60 v2 tasks | 60 | 12 | Delay vs task p50/p95 and queue time |
| Arrival rate | steady 0.25,0.5,1.0 tasks/s; two policies; 2 repeats | K=2, NP=4, same 60 v2 tasks and 2 s tools | 60 | 12 | Offered rate vs throughput, queue p95, task p95 |
| Context length | nominal 500,1500,2500-token initial documents; two policies; 2 repeats | K=2, NP=4, CTX=16384, 3 steps, 2 s tools, 64-token outputs | Same 40 synthetic tasks | 12 | Context vs task latency, computed/cached tokens, memory |
| Response length | forced 32,128,512 tokens; two policies; 2 repeats | K=2, NP=4, same 40 synthetic prompts | 40 | 12 | Output length vs latency and completed tasks/s |
| RAM cache | 0 vs 8192 MiB; two policies; 2 repeats | K=2, NP=4, same 60 v2 tasks | 60 | 8 | Cache budget vs server RSS, recomputation, latency |

Total if all groups run: **74 runs**, in stages. Start with a two-run K=2 check,
then the 18-run core. The other groups are independent; run them as time and
AWS credit allow. If a curve has a close or surprising comparison, add a third
repeat at *all* points on that curve before drawing a strong conclusion.
The current fixed set exposes `batch` and `steady` arrivals; bursty and Poisson
arrivals are supported by the older synthetic generator and can be separate
extensions. Shared-prefix and step-count sweeps are also extensions, not mixed
into these five figures.

## Inputs and launch commands

Generate the fixed subset and paired synthetic inputs once:

```bash
python -m scripts.select_validation
python -m workloads.build_phase1_sweeps
```

The synthetic builder uses the same task IDs, prompts, tool results, and arrival
times across context levels; only the initial document grows. Its output-length
variants have identical prompts and only change `max_tokens`. These runs have
**no reference accuracy score**. They use forced-length decoding so the output
curve has actual token counts close to 32/128/512. Check `requests.csv` for
short outputs or truncation before using the curve. Context sizes are nominal;
use measured prompt and cached tokens on the x axis when interpreting results.

Each command invokes both FIFOs, restarts the server before every run, and
stores raw data in `results/raw/<prefix>_r<repeat>_k<K>_<policy>/`. Use
`--dry-run` first. Commands below assume the repo root on the GPU machine:

```bash
# Core: 18 runs
python -m scripts.phase1_fifo --workload workloads/generated/validation_v2_60.jsonl \
  --prefix phase1_v2_batch --k 1 2 4 --repeats 3 --np 4 --ctx 16384 --cache-ram 0

# Tool-delay: 12 runs
for d in 0 2 8; do
  python -m scripts.phase1_fifo --workload workloads/generated/validation_v2_60.jsonl \
    --prefix phase1_delay_$d --k 2 --repeats 2 --np 4 --ctx 16384 --cache-ram 0 --tool-delay "$d"
done

# Arrival rate: 12 runs (numeric suffix is hundredths of a task/s)
for pair in 25:0.25 50:0.5 100:1.0; do
  label=${pair%%:*}; rate=${pair#*:}
  python -m scripts.phase1_fifo --workload workloads/generated/validation_v2_60.jsonl \
    --prefix phase1_rate_$label --k 2 --repeats 2 --np 4 --ctx 16384 --cache-ram 0 \
    --arrival steady --rate "$rate"
done

# Context and response lengths: 24 runs
for n in 500 1500 2500; do
  python -m scripts.phase1_fifo --workload workloads/generated/phase1_context_$n.jsonl \
    --prefix phase1_context_$n --k 2 --repeats 2 --np 4 --ctx 16384 --cache-ram 0
done
for n in 32 128 512; do
  python -m scripts.phase1_fifo --workload workloads/generated/phase1_output_$n.jsonl \
    --prefix phase1_output_$n --k 2 --repeats 2 --np 4 --ctx 16384 --cache-ram 0
done

# Cache extension: 8 runs
for mib in 0 8192; do
  python -m scripts.phase1_fifo --workload workloads/generated/validation_v2_60.jsonl \
    --prefix phase1_cache_$mib --k 2 --repeats 2 --np 4 --ctx 16384 --cache-ram "$mib"
done
```

Before every group, confirm that the `--dry-run` names are unused. The driver
refuses to overwrite an existing directory. Keep the model and source revision
fixed across all groups. If the instance uses a different repo or model path,
pass `--llama-root` and `--model` explicitly. Stop the EC2 instance after the
last run and copy raw results to the local repository for versioning.

## Reporting and plots

```bash
python -m analysis.phase1_report --prefix phase1_v2_batch --out results/phase1_v2_batch
python -m analysis.phase1_core_plots --report results/phase1_v2_batch
python -m analysis.phase1_sweep_report --stem phase1_delay_ --vary tool_delay \
  --axis-label 'Tool delay (s)' --out results/phase1_delay
python -m analysis.phase1_sweep_report --stem phase1_rate_ --vary rate --scale 0.01 \
  --axis-label 'Arrival rate (tasks/s)' --out results/phase1_rate
python -m analysis.phase1_sweep_report --stem phase1_context_ --vary workload \
  --axis-label 'Initial document tokens (nominal)' --out results/phase1_context
python -m analysis.phase1_sweep_report --stem phase1_output_ --vary workload \
  --axis-label 'Requested output tokens' --out results/phase1_output
python -m analysis.phase1_sweep_report --stem phase1_cache_ --vary cache_ram \
  --axis-label 'Host cache budget (MiB)' --out results/phase1_cache
```

The core report writes `runs.csv`, `types.csv`, and `repetitions.csv`, and the
core plot script adds K curves plus a task-type queueing figure. Each sweep
report writes `runs.csv`, `types.csv`, `points.csv`, and PNG curves with individual
repeat ranges shaded. Commit the reports alongside raw runs. Leave a group out
of the final comparison if any paired run is missing, a workload/model hash
differs unexpectedly, or context truncation invalidates its intended contrast.

## Report checklist

For every figure and table, include the denominator and repeat count:

- **Completion and errors:** offered, completed, failure/incomplete rate, status
  breakdown, HTTP/timeouts, missing steps, and context truncations.
- **Latency:** task p50/p95/p99 from arrival to finish, plus request p95,
  time to first token p95, and task/request queue p95. A slow steady arrival
  may lower queue time while reducing offered load; show both.
- **Throughput:** completed tasks/s and generated tokens/s over timed makespan.
  For fixed v2 tasks, show automatically correct judged tasks/s separately.
- **Memory/cache:** peak and initial GPU memory and server RSS, computed/cached
  prompt tokens, and per-step cache reuse. Fixed `CTX` may preallocate GPU KV,
  so a flat GPU-memory curve is a real finding, not a failed experiment.
- **Output and quality:** generated-token distributions, output-limit stops,
  short forced outputs, QA/multistep correctness, writing word-range compliance,
  and pending semantic writing judgments. Synthetic sweeps have no accuracy
  reference and cannot support claims about answer quality.
- **Fairness:** per-type completion and queue p50/p95, especially multistep and
  long QA versus short QA; show ratios and absolute times. A throughput gain
  should not hide long-task starvation.

Queue time is the available scheduling-cost measure for Phase 1. It includes
waiting for capacity, not just scheduler bookkeeping CPU time. If Phase 2's
policy has nontrivial decision logic, instrument its decision time separately.
