# Fixed task collection

`tasks/v1/` is a **draft development set** with 20 short-QA, 10 long-context QA,
and 10 long-generation examples prepared. The agreed target is 80 tasks: these
40 single-call tasks plus 40 multistep tasks, which are not yet populated.
It is not frozen and is not a held-out evaluation set.

## Short QA

Each task supplies a passage and asks one answerable question. It requires one
model request, no tools, and a short extractive answer. The examples use 20
different passages and source topics, covering entities, quantities, locations,
years, terminology, a process, and a mathematical property. Passage lengths are
74-158 whitespace-delimited words; these are word counts, not model token counts.

- `tasks/v1/short_qa.jsonl`: canonical task records, including evaluator-only answers.
- `tasks/v1/short_qa_review.md`: an index followed by every passage, question, and answer.

The records use unmodified contexts, questions, and answer annotations selected
from the SQuAD 1.1 development split. Repeated answer annotations are retained.
Each record includes the original question ID and downloaded dataset SHA-256.
This is a selected systems workload, not an official SQuAD benchmark run.
Selection favors short passages, direct questions, and source annotations that
agree on the answer text. It is intentionally a simple extraction workload, not
a representative random sample of SQuAD or a difficult reasoning benchmark.

## Long-context QA

- `tasks/v1/long_context.jsonl`: 10 synthetic retrieval tasks with exact references.
- `tasks/v1/long_context_review.md`: questions, answers, and full generated documents.
- `generate_long_context.py`: deterministic construction from recorded seeds.

The documents comprise three project registers, three shipment registers, two
equipment registers, and two incident registers. Each task asks for a labeled
field of one uniquely identified record. Distractors have the same format; each
target identifier and reference value appears once. Target records occur near
the beginning, middle, or end. Each task uses one model call and no tools.

These are original fictional documents inspired by the controlled retrieval
approach in RULER, not downloaded RULER tasks or an official benchmark evaluation.
This 10-task set mixes lengths and positions for a development pilot; it is too
small and not fully crossed to estimate independent effects of every dimension.

Documents contain 653-1,311 words. Full prompts contain 1,803-3,425 tokens using
the pinned upstream Qwen2.5-7B-Instruct tokenizer, including the system message,
document, question, and the runner's ChatML template. All leave at least 128
tokens of margin after the 32-token output budget under a 4,096-token limit.
The tokenizer revision and file checksum are stored per task. These are actual
upstream tokenizer counts, not word-based estimates; the deployed GGUF server's
tokenization and context capacity still need verification before measurement.

To reproduce the files, install `workloads/requirements-authoring.txt` and download
the pinned [tokenizer.json](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct/resolve/a09a35458c702b33eeacc393d103063234e8bc28/tokenizer.json).
Then, from the repository root:

```bash
python -m workloads.generate_long_context --tokenizer /path/to/tokenizer.json
python workloads/validate_tasks.py --tasks workloads/tasks/v1/long_context.jsonl --expected-count 10
```

The generator verifies the tokenizer checksum. Regeneration overwrites the two
long-context task files, so preserve any intentional edits before regenerating.

## Long generation

- `tasks/v1/long_generation.jsonl`: five technical explanations and five stories.
- `tasks/v1/long_generation_review.md`: prompts, per-task rubrics, and reference notes.
- `build_long_generation.py`: deterministic construction of the authored collection.

Technical topics are DNS, database indexes, HTTP caching, Python sorting, and a
native C compilation pipeline. The stories use lighthouse, lunar greenhouse,
railway station, forest journey, and baking contest settings. Each task requires
one model call and no tools. Source-linked technical reference notes are for
evaluation only; the model is not asked to browse or execute code.

Five tasks have a 512-token cap and request 200-280 words; five have a 1,024-token
cap and request 450-600 words. Both groups contain stories and explanations.
Generation uses temperature 0 and natural EOS. These are output maxima, not
forced token counts. Pilot actual outputs to confirm the requested word ranges
fit their token caps and generate enough work; revise/version the dataset before
comparative runs if necessary. Input prompts are 146-181 upstream Qwen tokens,
including the system instruction and ChatML, with evaluator metadata excluded.

Each task has four public content requirements and seven 0-2 rubric criteria.
Passing requires valid execution, at least 12/14 overall, no criterion below 1,
full correctness/consistency credit, the requested word range, and no listed
critical failure. Word counts use `len(text.split())` on the entire response.
These rules are fixed operational definitions for this development set, not
claims of universal writing quality. No responses have been generated or judged.
The QA exact-match scorer does not evaluate these writing tasks.

```bash
python -m workloads.build_long_generation --tokenizer /path/to/tokenizer.json
python workloads/validate_tasks.py --tasks workloads/tasks/v1/long_generation.jsonl --expected-count 10
```

The authoring command uses the same pinned tokenizer as long-context generation
and overwrites its two output files. For execution send the stored `system` and
`prompt` directly as system/user messages; exclude all `evaluation` fields.

## Review and validation

Run the offline structural and answer-span checks from the repository root:

```bash
python workloads/validate_tasks.py
```

These checks verify that records are well formed and every labeled answer exactly
matches the passage at its recorded character offset. They cannot establish that
a question is unambiguous or that its answer is semantically correct. Read the
examples in `short_qa_review.md` and flag concerns by task ID. There is no review
checklist, sign-off sheet, or approval gate. After corrections, rerun validation
and update the readable copy to match the canonical records.

No AWS inference has been performed. Short-QA tokenizer checks remain pending;
long-context and long-generation tasks have upstream tokenizer measurements.
Do not treat word counts or valid answer offsets as proof of deployed-server fit.

## Execution contract (next integration step)

The canonical records are separate from experiment arrival schedules and K.
They are **not directly accepted by the existing `runner.run` input format**.
When exporting a record, construct only this model input:

```text
System: Answer the question using only the passage. Return only the shortest
        answer span from the passage, with no explanation.

Passage:
{context}

Question: {question}
Answer:
```

Use each record's stored `system` instruction. For long-context QA replace the
`Passage:` label with `Document:` as in `generate_long_context.model_prompt`;
the recorded token counts correspond to that exact prompt.

The model receives neither the `evaluation` object nor source/review metadata.
The QA quality-validation settings are temperature 0, at most 32 output
tokens, and natural end-of-sequence stopping (`ignore_eos=false`). The current
client forces `ignore_eos=true` and the runner does not save or score response
text; those require a subsequent integration change before quality validation.

The offline scorer in `evaluation/score_qa.py` now implements QA scoring; see
[evaluation instructions](../evaluation/README.md) for the saved-output contract
and metric definitions. Runner output capture/export integration is still pending.
For short QA, it uses SQuAD-style normalized exact match and token F1 against
the best matching reference: lowercase, remove ASCII punctuation and English
articles (`a`, `an`, `the`), and collapse whitespace. An answer embedded in a
long explanation is not automatically an exact match. Numeric paraphrases such
as `eight` are not normalized to `8`; the prompt requests an extracted span.
Long-context identifiers use exact match with surrounding whitespace stripped;
punctuation and case remain significant, so `WH-123` and `WH123` are not equivalent.
Treat execution failures separately from incorrect answers.

## Attribution for SQuAD short-QA material

SQuAD was introduced by Pranav Rajpurkar, Jian Zhang, Konstantin Lopyrev, and Percy
Liang. The SQuAD dataset is distributed under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/); the selected
dataset material here retains that license. Passage text originates from Wikipedia
articles identified by the source titles. No passage, question, or answer edits
have been made; project IDs, prompts, and metadata were added.

- [SQuAD project and license information](https://rajpurkar.github.io/SQuAD-explorer/)
- [SQuAD 1.1 development data](https://rajpurkar.github.io/SQuAD-explorer/dataset/dev-v1.1.json)
- [Original paper](https://aclanthology.org/D16-1264/)

Keep source attribution and license information with redistributed task records.
