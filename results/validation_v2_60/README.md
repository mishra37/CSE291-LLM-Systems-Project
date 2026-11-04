# Sixty-task Qwen validation

This is a real-model readiness run, not a FIFO comparison. It uses the fixed
[selection](selection.json) created by
[`scripts/select_validation.py`](../../scripts/select_validation.py): 10 short QA,
all 10 long-context QA, all 10 writing tasks, and 30 multistep tasks (8 sales,
8 logs, 7 documents, 7 inventory). The selection contains **60 of 80** v2 tasks,
182 planned model calls, and 122 planned tools. All selected task records match
the raw run's offered manifest in the same order. The selection checksum is for
the compact JSONL serialization; `offered_tasks.jsonl` uses spaced JSON and has
different bytes despite identical records. Source-file checksums in the
selection manifest normalize CRLF to LF, matching the repository's stored task
files on Windows and Linux.

Run: AWS g6.xlarge/NVIDIA L4, Qwen2.5-7B-Instruct Q4_K_M, llama.cpp commit
`785322d17f2d51e5185cf996a1f4e46d87640841`, model SHA-256 in the saved
[checksum](../smoke_2026-11-04/model.sha256). Request FIFO, K=2, NP=4,
CTX=16384 (4096 per slot), host cache off, batch arrivals, task defaults of
2 seconds per scripted tool call, temperature 0, natural EOS. The server was
restarted before the run and given the runner's one-request warm-up. See the
[raw run](../raw/validation_v2_60_request_k2/) for the schedule, exact offered
tasks, prompts/responses, events, request/task CSVs, memory samples, and config.
The [source snapshot](source_snapshot.tar.gz) is the transferred code and v2
tasks used on EC2, with SHA-256
`bd183b9dec319c8855146bb07f92d81b8c3755a000b3514f4a046da0400d7e88`;
it builds on Git commit `555d9b4` with the subsequent local runner/v2 changes.
The remote archive lacked `.git`, so the runner's `config.json` has an empty
`git_commit`; the snapshot and this record identify the code instead.

| Measure | Result |
|---|---:|
| Tasks with all planned model calls completed | 60/60 |
| Model requests / scripted tools | 182 / 122 |
| HTTP/tool/timeouts / context truncations | 0 / 0 |
| Task completion latency p50 / p95 / p99 | 137.280 / 362.794 / 365.112 s |
| Measured makespan / completed-task throughput | 365.13 s / 0.1643 tasks/s |
| Peak GPU memory / server RSS | 5922.9 / 872.7 MiB |
| Short QA / long-context QA exact matches | 10/10 / 9/10 |
| Multistep final JSON exact matches | 13/30 |
| Writing responses within word range | 5/10 |
| Writing semantic judgments | Pending |

Multistep correctness by subtype: sales **0/8**, logs **7/8**, documents **6/7**,
inventory **0/7**. The references and strict scorer were unchanged. The low
arithmetic accuracy is a model-quality limitation for this workload; do not
silently count those tasks as correct or discard them from denominators. The
single missed long-context QA task is `long_context-v2-005`.

There were **74 output-limit stops in intermediate multistep calls** (out of
122 such calls) and one writing output-limit stop. None of the 30 final
multistep calls hit its 256-token cap. Output-limit stops are recorded in
`requests.csv` and are separate from context truncation; the runner completed
the scheduled workflow in each case. Intermediate limits and answer-length
variation need to stay visible in subsequent policy comparisons. The 10 writing
responses still require rubric scoring; 5 already fail the mandatory word range.

These are single-run observations at K=2. The high batch-arrival latency includes
queue time. They do not establish the best K, a policy advantage, memory saturation,
or stable tail estimates. The remaining 20 v2 tasks were not exercised by this
real-model validation. The earlier local HTTP test replayed all 80 definitions
through both FIFO policies, and the offline collection validator checks all 80
records and references.
