# Task v2 calibration — November 4, 2026

This run checks the revised prompts and output budgets against the real Qwen model.
It is not a FIFO performance comparison or a claim that every task is now answered
correctly. The original [v1 smoke results](../smoke_2026-11-04/README.md) are preserved.

## Changes and setup

The [v2 collection](../../workloads/tasks/v2/README.md) has explicit public field
types, clearer final-step JSON instructions, a 256-token final response allowance
(intermediate steps remain 128), and stronger whole-response writing-length
instructions. Reference answers, fixtures, scoring, and writing word ranges did
not change. No responses were trimmed, retried for best-of selection, or corrected
before scoring. Valid syntax and correct values are reported separately.

Each policy received 16 tasks: the first short QA and long-context QA, all ten
writing tasks, and task 001 from each of the four multistep subtypes. Hardware,
model checksum, llama.cpp revision, and Python environment match the earlier smoke
test on instance i-0bc382cd3410d752d. Conditions: K=1, NP=4, CTX=16384, host cache
disabled, batch arrival, 0.1-second tool delays, temperature 0, natural EOS.
The server was restarted and identically warmed before each policy run.

The exact remote driver is [llmsys-calibrate-v2.py](llmsys-calibrate-v2.py).
It has the original remote paths and output names; use new names for repeats.
Each raw run contains the complete offered definitions, schedule, and deployment
metadata. The source snapshot SHA-256 is
`bd183b9dec319c8855146bb07f92d81b8c3755a000b3514f4a046da0400d7e88`.
It includes the uncommitted integration and v2 changes on base commit 555d9b4.

## Results

| Check | Request FIFO | Task FIFO |
|---|---:|---:|
| Execution completions | 16/16 | 16/16 |
| Model calls / tool calls | 26 / 10 | 26 / 10 |
| Execution errors / context truncations | 0 / 0 | 0 / 0 |
| QA exact matches | 2/2 | 2/2 |
| Multistep final JSON shape/types valid | 4/4 | 4/4 |
| Multistep final output-limit stops | 0/4 | 0/4 |
| Multistep answers with all values correct | 1/4 | 1/4 |
| Writing word-range compliance | 5/10 | 5/10 |
| Writing semantic rubrics | Pending | Pending |

The four final JSON responses now have the requested field types and no Markdown
fences. The document answer, previously rejected for fences, passes. Other failures
remain substantive:

- Sales still returns 520 instead of 540.
- Logs return the correct ID chain, but incorrectly identify checkout/
  DB_REQUEST_FAILED as its origin instead of database/POOL_EXHAUSTED.
- Inventory incorrectly counts both SKUs as short and reports 10 shortage units;
  only SKU01-1 is short, by 5 units.

These values and strict scoring are unchanged. A larger cap and clearer format do
not repair arithmetic or reasoning. The experiment changes prompts and caps
together, and has a larger workload than the v1 smoke test, so it does not isolate
the individual effect of each change. The successful final JSONs fit below even
the old 128-token cap; the new 256 cap provides headroom, not a demonstrated need.

## Writing lengths

Word counts use `len(text.split())` on the entire response. No output is a semantic
quality pass merely because it satisfies the word range.

| Task suffix | Required words | Request FIFO | Task FIFO |
|---|---:|---:|---:|
| 001 DNS | 200–280 | 290 (fail) | 371 (fail) |
| 002 indexes | 450–600 | 463 | 481 |
| 003 HTTP caching | 200–280 | 325 (fail) | 331 (fail) |
| 004 sorting | 450–600 | 499 | 526 |
| 005 compilation | 450–600 | 745 (fail) | 697 (fail) |
| 006 lighthouse | 200–280 | 290 (fail) | 330 (fail) |
| 007 greenhouse | 450–600 | 465 | 484 |
| 008 station | 200–280 | 272 | 280 |
| 009 forest | 450–600 | 618 (fail) | 571 |
| 010 baking | 200–280 | 259 | 295 (fail) |

The compilation explanation hits the 1,024-token cap under request FIFO. The
second model calls in the log and inventory workflows hit their 128-token
intermediate caps under both policies. These stops are preserved in the request
records; all final multistep responses end naturally. Context truncation is a
different condition and was not observed. Word-range compliance remains a model
limitation despite clearer instructions; do not enlarge the allowed ranges or
truncate saved responses retroactively.

## Remaining work

Run the full 80 tasks after this development calibration, assess the other 36
multistep tasks, and score writing content with the fixed rubric. Any further
prompt experiments need a new recorded revision. Establish per-family accuracy,
output-length variation, and output-cap rates before drawing FIFO performance
conclusions. The raw quality files retain `judgment=pending` for writing; a known
length failure already rules out an overall pass even while semantics are pending.

Raw runs: [request FIFO](../raw/calibration_v2_fifo_request/),
[task FIFO](../raw/calibration_v2_fifo_task/). [diagnostics.json](diagnostics.json)
records field-type checks, word counts, cap stops, and measured resource summaries.
