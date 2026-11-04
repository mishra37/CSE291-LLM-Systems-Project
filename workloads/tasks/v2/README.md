# Task collection v2

80 draft development tasks, derived deterministically from v1. Use this directory
for new calibration runs. The v1 collection and its recorded smoke results remain
unchanged. Each v2 record stores its parent task ID and canonical parent checksum.

## Changes

- All 40 multistep prompts now declare every final field's type. Event and section
  chains explicitly contain ID strings, not event/section objects.
- Final-step instructions repeat the public field contract and require one compact
  JSON object with no fences or explanation. They ask the model to recheck raw tool
  data because earlier assistant summaries can be wrong.
- Intermediate caps remain 128 tokens; the final cap is 256. The runner honors
  the per-step override, and context budgeting includes it. Estimated peak budgets
  are 1,139–2,603 tokens including a 128-token margin, below the 4,096-token limit.
- All ten writing prompts repeat the original whole-response word range, give a
  target length, and instruct the model to plan/review its length. Their caps remain
  512/1,024 tokens; rubrics and word ranges are unchanged. Inputs are 260–296 upstream
  Qwen tokens including ChatML.
- QA model inputs, all fixture data, tool order/counts, reference values, and scoring
  rules are unchanged. Version IDs and lineage metadata do not enter model prompts.

These are prompt and budget changes, not answer injection, automatic retries, reply
trimming, or relaxed scoring. A valid JSON response can still have incorrect values.

## Reproduction

Use the pinned tokenizer described in [the workload guide](../../README.md).

```bash
python -m workloads.build_v2 --tokenizer /path/to/tokenizer.json
python -m workloads.validate_collection --tasks-dir workloads/tasks/v2
python -m unittest discover -s tests -v
```

The builder overwrites generated v2 JSONL and review files. Treat further prompt
changes after recorded runs as another revision, and retain the old run artifacts.

## Validation so far

All 80 definitions validate; deterministic regeneration and 24 software tests pass.
On AWS, both FIFO policies completed a 16-task calibration set: two QA controls,
all ten writing tasks, and one task per multistep subtype. All four multistep final
answers passed the strict JSON shape/type checks with no final output-limit stops.
Only the document task had entirely correct values; writing length compliance was
5/10 for each policy. Semantic writing evaluation is pending. Some intermediate
responses still reach their fixed cap.

See the [calibration report](../../../results/calibration_v2_2026-11-04/README.md)
for the failures and exact run conditions. This is not a full-collection inference
validation or a policy-performance comparison. The additional final allowance is
headroom; this run does not isolate its benefit from the prompt changes.

## Review files

- [Short QA](short_qa_review.md)
- [Long-context QA](long_context_review.md)
- [Long generation](long_generation_review.md)
- [Multistep workflows](multistep_review.md)

SQuAD-derived QA material retains its original source attribution and CC BY-SA 4.0
license; see [the attribution](../../README.md#attribution-for-squad-short-qa-material).
