# Audit of the earlier v1 sweeps

This audits the saved v1 results described in the main README, separately from
the controlled v2 run now in progress. The older sweeps are development evidence,
not final repeated estimates.

## What was checked

- All **33** `sw_*` run directories with a `summary.json`: 8 slot, 6 tool-delay,
  6 arrival-rate, 9 synthetic-context, and 4 KV-configuration runs.
- `tasks.csv`, `requests.csv`, `predictions.jsonl`, `summary.json`, and
  `config.json` row counts/statuses. The 24 fixed-v1 runs also have
  `quality/quality_summary.json`; their QA, multistep, and writing-length
  totals were recomputed from saved predictions and canonical v1 references.
- The saved `results/runs_summary.csv` task counts, latency, throughput,
  memory, and quality fields were compared with the source run summaries.

**Result:** the checked summary fields match the raw files. All 33 directories
have the expected number of predictions. **32/33** sweeps completed every
offered task. The exception is
[`sw_kv_split16k_gpuonly_fifo_request`](../results/raw/sw_kv_split16k_gpuonly_fifo_request/):
73/80 completed; seven long-context prompts received HTTP 400 because the
2,048-token per-slot limit was too small. That run cannot be called a speed win
over complete 80/80 runs. These checks verify recorded execution and scorer
arithmetic; they do not independently prove every task reference is correct.

## What the sweeps actually vary

| Sweep | Saved observations | Limit on interpretation |
|---|---|---|
| Slots | `K=NP=2,4,8,16` and `CTX=4096×NP`; 80 fixed v1 tasks, two FIFOs | Scheduler concurrency, number of server slots, and total allocated KV memory change together. It is a serving-capacity curve, not a fixed-server K-only curve. |
| Tool delay | 0.5, 5, 10 s at K=NP=4, plus a 2 s point from the slot sweep | Same v1 tasks, but each cell ran once. The large 10 s task-FIFO penalty is observed; precise break-even needs repeats. |
| Arrival rate | Poisson 0.25, 0.5, 1.0 tasks/s at K=NP=4 | Same canonical tasks and seed; one replay per cell. Makespan includes the arrival span, so report offered rate and task latency alongside throughput. |
| Synthetic context | Nominal 1k, 4k, 12k initial documents; 40 tasks per run | The generator produced **15 multistep agents and 25 short QA tasks**, not 20+20. It reused one RNG across task creation, so changing document size also changed most task instructions, short questions, and tool texts. These are not paired size-only inputs. No reference accuracy score exists. |
| KV configuration | Split 16k, unified 16k, and 8-bit KV compared with the standard 32k K=8 run | The split 16k run failed 7 tasks. Unified KV reduced observed whole-GPU memory from 6,813 to 5,937 MiB. QA scores match across the complete runs, but multistep scores and generated text vary. |
| KV restore microbenchmark | 30k-token, 3 trials per storage mode, one slot | RAM restore ≈1.24 s, EBS and NVMe restores ≈13.06 s, GPU-retained ≈0.04 s. Effective restore rate is ≈132 MB/s for a 1.72 GB slot file. The measurements alone do not separate disk bandwidth, llama.cpp loading, and memory-copy costs. |

In the synthetic context sweep, measured median **initial** multistep prompts
were approximately **983, 3,499, and 10,128 tokens**. The 1k/4k/12k labels
are nominal generator settings. Regenerating the inputs from the recorded seed
and code gives the same 15/25 type mix at all three settings, but among the 15
agents only **1** kept the same task instruction and **0** kept the same later
tool inputs when moving from nominal 1k to 12k. Only **2/25** short-question
prompts were identical. The large latency difference is suggestive, but cannot
be attributed only to document length.

## Quality and output checks

The five 80-task runs in the main README all completed 80/80, and the **30 QA
response texts were identical** across them (28/30 correct). Multistep exact
scores were **9–12/40**; even the repeated request-FIFO configuration flipped
six individual multistep correctness outcomes while staying at 9/40 total.
Writing responses met their required word ranges in only **1–4/10** tasks,
depending on the run; writing semantics were not judged. The five runs generated
29,105–30,133 tokens, a **3.4%** range relative to the largest total, rather
than a range within 2%.

The first GPU-only request-FIFO run had **124 output-limit stops in 172
intermediate multistep calls**, and 9/40 multistep final calls hit their limit.
Among its incorrect multistep answers, 18 had wrong or missing fields and 13
were not valid JSON. The low score therefore cannot be described solely as
arithmetic mistakes. Completion of all scheduled calls is distinct from
correctness or compliance with output requirements.

The 8-bit KV run scored **13/40** multistep answers versus **9/40** for the
standard K=8 request-FIFO run; QA stayed **28/30**, and writing word-range
compliance was **2/10 versus 3/10**. “Same answers” is not accurate. These
differences could reflect batching variation; the single runs do not isolate
an 8-bit KV quality effect.

## Provenance and reuse

[`scripts/sweep.sh`](../scripts/sweep.sh) restarts llama-server before each
sweep run. The earlier synthetic pilot did not restart between its two policies
and remains a rough comparison. The sweep `config.json` files record workload
metadata and a model path, but not a per-run workload hash, model checksum, or
llama.cpp commit. An environment snapshot records the runtime once. Source
revisions changed during the sweep collection; the changes between the two
recorded revisions affected the sweep and microbenchmark scripts, not the task
generator or runner. Synthetic generated JSONL inputs were not committed, so
the exact prompt bytes cannot be recovered from the raw run folders alone.

The original sweep script continues after a failed launch or runner invocation
and can still print a group-level `done` message. The run-directory checks
above, rather than that message, establish which saved runs completed. The
context plot also originally labeled the mix as 20 agents plus 20 questions;
the regenerated plot now uses the recorded 15/25 mix. Its prompt-evaluation
panel sums request-level durations, so it is not exclusive GPU time.

The strongest provisional trends are the slot-capacity/throughput trade-off,
task FIFO's long-wait penalty, and context-recomputation cost. Small speed and
quality differences need repeated, paired runs. The new v2 protocol keeps NP
and CTX fixed while sweeping K, records workload/model/runtime checksums, and
builds paired synthetic context and output-length inputs.
