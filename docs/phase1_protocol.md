# Phase 1 FIFO comparison protocol

The [experiment matrix](phase1_experiment_matrix.md) lists the full launch
sequence and the five performance curves built from this protocol.

The existing [v1 results](../README.md#results-so-far) are useful development
measurements. The new controlled comparison uses the fixed, reproducible
[v2 selection](../results/validation_v2_60/selection.json): 60 tasks, comprising
10 short QA, 10 long QA, 10 long generation, and 30 multistep tasks. Using all 80
is unnecessary for every sweep. Keep the other 20 available for a later check
of whether a conclusion depends on this selection.

## Run controls

On the GPU machine, check out the same repository revision for all runs and
pin the llama.cpp revision and Qwen2.5-7B-Instruct Q4_K_M model. Generate the
selection once:

```bash
python -m scripts.select_validation
python -m scripts.phase1_fifo --workload workloads/generated/validation_v2_60.jsonl \
  --prefix phase1_v2_batch --k 1 2 4 --repeats 3 --np 4 --ctx 16384 \
  --cache-ram 0 --arrival batch --dry-run
```

The same command without `--dry-run` executes 18 runs. Expect several hours;
do a two-run check before launching the full matrix. Each run has a unique name
and refuses to overwrite prior data. For every policy and repeat, the driver
restarts llama-server, clears its prior cache, then the runner issues the same
one-request warm-up before starting the clock. The driver writes
`deployment.json` with workload, model, runtime, and source checksums. It keeps
`NP=4` and total `CTX=16384` fixed while varying scheduler `K`. This prevents
a K sweep from also changing the server's per-slot context allocation. The
server has 4096 tokens per slot; verify zero context truncations in every run.

Use task defaults for 2 s tool delays in the main comparison. Change one
dimension at a time for follow-up curves: `--arrival steady --rate <tasks/s>`,
`--tool-delay <seconds>`, `--cache-ram 8192`, or a separately documented
`CTX`/`NP` configuration. A RAM-cache run must use the same fresh-server
procedure for both FIFOs. Do not mix runs with different workload or model
checksums in one comparison. The analysis script rejects such mixtures.

## Reporting

```bash
python -m analysis.phase1_report --raw results/raw --prefix phase1_v2_batch \
  --out results/phase1_v2_batch
```

This produces `runs.csv` (one row per run), `types.csv` (one row per task type
per run), and `repetitions.csv` (median over repeated runs per policy and K).
Keep raw `tasks.csv`, `requests.csv`, `memory.csv`, `quality.jsonl`, prompts,
responses, and `deployment.json` alongside them. Plot K against throughput,
p50/p95 task latency, queue p95, peak GPU and server RSS, completion and
correctness counts. Show individual repeats, not only medians. A later arrival,
context, delay, or output-length sweep needs its own labeled comparison.

Definitions:

| Measure | Definition |
|---|---|
| Offered | Tasks in the fixed input manifest; never remove failures from this denominator. |
| Completed | All planned model calls returned a terminal, nonempty response, with no context truncation. |
| Failure / incomplete | Offered minus completed; report HTTP, timeout, empty, truncation, and other statuses separately from raw logs. |
| Task latency | `t_done - t_arrive`, from scheduled arrival to terminal task state; p50/p95/p99 use completed tasks, with incomplete count alongside. |
| Queue time | Task admission wait plus its request queue waits. Report task p50/p95 and model-request queue p95. |
| Throughput | Completed tasks divided by timed replay makespan, including batch drain time. Also report generated tokens and automatically correct judged tasks per second. |
| Peak memory | Maximum sampled GPU memory and llama-server RSS during timed replay; 100 ms samples can miss shorter spikes. Record server RSS at run start too when diagnosing cache. |
| Correctness | Exact QA and typed final JSON for multistep, across all offered scored tasks. Writing semantic judgments are pending; report writing word-range compliance separately. |
| Output integrity | Generated tokens, final and intermediate output-limit stops, missing steps, and context truncations; a terminal output-limit stop is not a transport failure but may harm quality. |
| Long-task fairness | Per-type p50/p95 completion and queue time, plus number completed/correct for multistep and long QA. Check their tails before claiming a throughput win. |

The scheduler's `queue_s` is waiting time, not isolated scheduler CPU overhead.
Runtime cost of the policy will need a separate bookkeeping measurement for
Phase 2. `correct_judged_tasks/s` excludes pending writing judgments from its
numerator, while the offered and unjudged counts remain visible. The prior
[60-task validation](../results/validation_v2_60/README.md) completed all
workflow steps but produced only 13/30 correct multistep final answers; this
model-quality limit must remain in the report.

Select the best fixed-concurrency setting using development runs. Then compare
the memory-aware policy against both FIFO policies and that tuned setting on a
separately labeled evaluation mix. Do not select K using the final evaluation
result. Report cases with little or no improvement as well as favorable cases.
