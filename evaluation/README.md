# Task completion and quality

Report execution and quality separately. An HTTP-successful request can still
give a wrong answer. Every offered task stays in the denominator, including
missing tasks, errors, timeouts, and invalid completions.

| Metric | Definition |
|---|---|
| Completion rate | Validly completed tasks / all offered tasks |
| Accuracy among completed QA tasks | Correct completed answers / validly completed tasks |
| Success rate across all offered QA tasks | Correct completed answers / all offered tasks |
| Correct-task throughput | Correct completed answers / measured experiment duration |

Example: ten offered tasks, nine completed, eight correct means 90% completion,
88.9% accuracy among completed, and 80% success overall. If nothing completes,
accuracy among completed is undefined (`null`), while overall success is zero.

For these QA tasks, a valid execution requires status `ok`, all planned model
calls completed, a terminal completion message observed, nonempty output, and no
context truncation. Reaching an output limit does not by itself establish answer
correctness; score the returned text. A missing terminal message is not completion.

## QA scoring (implemented offline)

- Short QA: SQuAD-normalized exact match plus token F1 against the best reference.
- Long-context QA: exact match after stripping surrounding whitespace. Preserve
  identifier punctuation and case. Extra explanations do not pass exact match.
- Failed or missing tasks receive zero credit. F1 is only reported for SQuAD QA;
  it is not an appropriate partial-credit measure for random identifiers.
- The reference answers are evaluator-only and must never be included in a prompt.

The scorer accepts one saved final result per offered task. Example input line:

```json
{"task_id":"long_context-v1-001","status":"ok","steps_done":1,"response_complete":true,"truncated":false,"text":"123456"}
```

The number above is only an illustration, not a reference answer. All five fields
besides `task_id` are required. `response_complete` means the model stream's
terminal completion message was actually received for the completed task, not
simply that an HTTP request returned 200. `truncated` records context truncation.
For a timeout use `status="timeout"`, an appropriate `steps_done`, and
`response_complete=false`; any partial text may be preserved. Omitted task IDs
are counted as missing. Unknown or duplicate IDs are rejected, preventing accidental
best-of-retry scoring or denominator changes. Use a distinct run ID outside this
file when scoring separate experimental repetitions.

Once the runner has saved predictions, score exactly its offered manifest:

```bash
python -m evaluation.score_qa --tasks workloads/tasks/v1/long_context.jsonl --predictions results/raw/my_run/predictions.jsonl --out-dir results/raw/my_run/quality
```

For a run offering both QA families, pass both task files after `--tasks`. For a
subset run, supply the exact offered subset, not the whole collection. Optionally
pass `--makespan-s` from that run to calculate correct-task throughput.

Outputs are `quality_tasks.csv` and `quality_summary.json`, including counts,
rates, per-family metrics, and input-file checksums. These commands do not call a
model or an external judge. Unit checks run with:

```bash
python -m unittest discover -s tests -v
```

**Integration status:** the existing performance runner does not yet export this
predictions schema or consume the canonical task files. It also forces EOS to be
ignored. Connecting the task exporter, natural-EOS settings, response capture,
and reliable terminal/truncation flags to the runner is still required. Current
test scores are synthetic checks, not measured Qwen accuracy. Existing pilot
summary completion counts use the older, less strict definition.

## Long generation (task rubrics created; judging integration pending)

Stories and explanations do not have a single exact answer. The ten tasks in
`workloads/tasks/v1/long_generation.jsonl` now contain fixed rubrics, critical
failure rules, word ranges, and evaluator-only reference notes. Keep three measures:

1. Execution completion as above.
2. Mechanical requirements, such as required headings and any task-specific
   minimum length, plus actual generated tokens and finish reason. Do not call
   every short answer a failure: use the task's declared requirements. A maximum
   output budget is not a minimum, and forced token generation is not evidence
   of coherence or quality.
3. Quality: instruction coverage, coherence, unnecessary repetition, and factual
   correctness for explanations or consistency for stories. Record scores per
   criterion. Define a pass threshold and any critical-failure rules in the task
   rubric before comparing schedulers. Quality success rate uses all offered
   tasks, not just attractive or completed outputs.

For the initial ten tasks, human scoring is manageable. A stronger LLM can later
apply the same rubric to saved outputs, outside the timed experiment. Fix the
judge model/version, prompt, settings, and rubric; hide scheduler labels; give
the judge the original task and answer; save its reasons and scores; manually
audit a sample and disagreements. Treat unscored judge failures as pending
evaluation, report their count, and do not silently remove them from comparisons.
Report evaluation cost separately from serving performance.

The current rubric has seven criteria, each scored 0/1/2 (unmet/partial/met).
Pass requires at least 12/14, at least 1 on every criterion, 2 on correctness or
story consistency, the public word range, valid execution, and no critical
failure. Count words with `len(text.split())` over the whole response. Record
per-criterion evidence as well as the total; a high total cannot override a
critical error. All these rules are in the task records and the readable
`long_generation_review.md`. Sources support the technical reference notes;
they are not extra input for the serving model.

For example, 14/14 with an unmet length requirement does not pass this dataset's
quality rule, while 12/14 can pass if all other conditions hold. Report length
compliance and semantic scores separately so that distinction remains visible.
Do not pass these tasks to `score_qa.py`: that evaluator intentionally rejects
`long_gen`. Automated rubric-score aggregation and judge integration remain
future work; creating a rubric does not measure any model's actual quality.

LLM judging is a fallible quality estimate, not ground truth: the
[MT-Bench judge study](https://arxiv.org/abs/2306.05685) discusses position,
verbosity, and self-enhancement biases. No judge service is connected or invoked
by the current evaluator.
