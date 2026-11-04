# First fixed-task smoke test — November 4, 2026

Real Qwen inference on instance i-0bc382cd3410d752d (NVIDIA L4), with
Qwen2.5-7B-Instruct Q4_K_M and llama.cpp commit
785322d17f2d51e5185cf996a1f4e46d87640841. Model checksum, environment,
Python package versions, and the exact remote driver are saved here.

The deployment used base project commit 555d9b4 plus the uncommitted runner
integration. Each raw run contains deployment.json with the transferred archive
checksum. The driver uses its original remote paths and refuses to overwrite
existing output directories; use new run names for repetitions.

Seven tasks: the first short QA, first long-context QA, first writing task, and
first task of each multistep subtype. Both policies use K=1, NP=4, CTX=16384,
cache RAM 0, batch arrivals, natural EOS, temperature 0, and 0.1-second tool
waits. The server was restarted before each policy and the same warm-up applied.
This is one execution/quality smoke test, not a controlled policy benchmark.

| Metric | Request FIFO | Task FIFO |
|---|---:|---:|
| Execution completions | 7/7 | 7/7 |
| Model calls / tool calls | 17 / 10 | 17 / 10 |
| Errors / context truncations | 0 / 0 | 0 / 0 |
| Measured replay duration | 38.87 s | 35.70 s |
| Peak GPU memory | 5920.9 MiB | 5916.9 MiB |
| Peak server RSS | 857.2 MiB | 848.7 MiB |
| QA exact matches | 2/2 | 2/2 |
| Multistep final JSON passes | 0/4 | 1/4 |
| Writing words (required 200–280) | 370 | 359 |

## Quality findings

- Sales returned 520 rather than the reference total 540 in both runs.
- Log answers attempted verbose event objects and hit the 128-token cap. The
  reference expects an ordered array of event IDs. Review the public prompt's
  schema clarity before deciding how to calibrate this task.
- Document answers had the correct values but included Markdown fences, which
  violate the explicit raw-JSON instruction and fail the current strict scorer.
- Inventory hit the output cap while explaining calculations under request FIFO;
  it returned the correct final JSON under task FIFO.
- Both writing responses exceeded the word range. They ended naturally (456 and
  444 tokens), rather than hitting the 512-token cap. Semantic rubric scoring
  remains pending; the known length failure already prevents an overall pass.

Execution completion means all planned requests returned valid terminal responses;
it does not mean a final answer is correct or complete in meaning. Output-limit
stops remain visible in requests.csv and are distinct from context truncation.

The differences in answers despite temperature 0 mean these small runs cannot
establish a scheduler quality or performance advantage. Before larger sweeps,
review prompt/schema clarity and final-answer budgets on development tasks,
version any changes, then rerun the same tasks and scoring rules across policies.
Do not relax scoring retroactively to make these saved results pass.

## Raw artifacts

- [Request FIFO](../raw/smoke_fixed_fifo_request/): prompts/responses, predictions,
  tool events, quality results, schedules, timing CSVs, memory samples, summaries.
- [Task FIFO](../raw/smoke_fixed_fifo_task/): the same artifacts for task FIFO.

The full 80-task collection has not yet been run against the real model.
All 19 software tests also passed on this AWS machine before inference.
