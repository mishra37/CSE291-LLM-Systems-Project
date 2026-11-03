# Memory-aware scheduling for agent workloads on llama.cpp

CSE 291 (LLM Systems) project. The core question is: **how can admission and
scheduling improve completed agent work while keeping memory use bounded?**
Phase 1 measures fixed-concurrency FIFO baselines; Phase 2 will build one
memory-aware policy motivated by those measurements.

## Current status

- Two FIFO schedulers, a synthetic workload runner, memory/request/task
  instrumentation, and a four-run AWS pilot are implemented.
- The fixed development collection now contains **80 tasks** across four families,
  with readable review files, reference answers or rubrics, and offline validation.
- QA scoring is implemented offline. The fixed collection still needs runner
  integration, tool-fixture execution, response capture, and quality evaluation
  on the serving model. No inference results exist for these 80 tasks yet.
- Controlled performance curves, a tuned fixed-concurrency baseline, and the
  Phase 2 memory-aware policy remain to be implemented/evaluated.

The recorded pilot used AWS g6.xlarge, one NVIDIA L4, CUDA llama.cpp
`llama-server`, and Qwen2.5-7B-Instruct Q4_K_M. Environment snapshots are in
[results/](results/); setup instructions are in [setup/README.md](setup/README.md).
These describe the recorded environment, not the current state of an EC2 instance.
Keep the model, precision, and runtime revision fixed for comparisons; the setup
script's default upstream branch is not a pinned reproduction of the recorded build.

## What the two FIFO policies do

A **model call** asks the local model to generate a response. A **tool call**
obtains external information, such as sales rows or a log bundle. An **agent task**
may alternate between them while retaining the conversation from earlier steps.

`K` is the scheduler's concurrency limit. It controls different units in the two
policies in [scheduler/fifo.py](scheduler/fifo.py):

| Policy | What waits in FIFO order | Meaning of K | During a tool delay |
|---|---|---|---|
| `fifo_request` | Each ready model request, including later steps of an existing task | At most K model requests in flight | Releases request capacity; the next model step rejoins the queue |
| `fifo_task` | Whole tasks awaiting admission | At most K admitted tasks | Keeps its admission and assigned server slot until the task finishes |

For example, with `K=2`, request FIFO can serve another task while a sales task
waits for data. Task FIFO can admit only two tasks, even when both are waiting on
tools. Request FIFO lets llama-server choose slots; task FIFO explicitly pins
each admitted task to one slot. Pinning can preserve reusable context, while
request FIFO may require context to be restored or recomputed. Neither policy
is universally better: the result depends on delays, context size, cache behavior,
and the workload mix.

`NP` is the server's number of parallel slots, separate from application-level
`K`. In the recorded configuration, `CTX=16384` and `NP=4` provide 4,096 context
tokens per slot. Keep `NP >= K` for these baselines, especially because task FIFO
uses explicit slot IDs. Increasing `NP` at fixed total `CTX` changes per-slot
capacity; changing both `K` and `NP` is not a pure scheduler-concurrency sweep.

The pilot compares `--cache-ram 0` and `--cache-ram 8192` (an 8,192 MiB host-cache
budget). Releasing application request capacity does not erase server caches or
the task history held by the runner. Cache retention and memory savings must be
measured rather than inferred from the scheduler alone.

## Fixed task collection: 80 tasks

Canonical JSONL definitions live in [workloads/tasks/v1/](workloads/tasks/v1/).
This is a draft development set, not a frozen or held-out benchmark. The
[manifest](workloads/tasks/v1/manifest.json) records counts and canonical JSON
checksums. Read [workloads/README.md](workloads/README.md) for schemas, provenance,
authoring commands, and the execution contract.

| Family / stored type | Tasks | Model calls per task | Tool calls per task | Main workload dimension |
|---|---:|---:|---:|---|
| Short QA / `short_qa` | 20 | 1 | 0 | Small input and short output |
| Long-context QA / `long_context` | 10 | 1 | 0 | Large input, retrieval within supplied context |
| Long generation / `long_gen` | 10 | 1 | 0 | Short input and long output |
| Multistep / `multistep` | 40 | 3, 5, or 8 | 2, 4, or 7 | Dependent requests, tool waits, growing history |
| **Total** | **80** | **252 planned calls** | **172 planned calls** | Counts assume every task reaches its final step |

The two earlier [preview tasks](workloads/tasks/previews/multistep_review.md)
are separate examples, not two additional tasks in the total.

### Short QA: 20 extractive questions

Each task gives a passage and asks for its shortest answer span. The passages
are 74–158 words, selected from 20 different SQuAD 1.1 development passages and
source topics. Questions cover names, locations, quantities, years, terminology,
a process, and a mathematical property. Original passages, questions, answer
offsets, source IDs, and attribution are retained. This selection is a small
systems workload, not an official SQuAD benchmark evaluation.

Complete prompts contain 144–328 tokens with the pinned upstream Qwen tokenizer.
Each task uses one model call, no tools, temperature 0, natural EOS, and a
32-token output maximum. Score with SQuAD-style normalized exact match and token
F1 against the best reference. Source material retains its CC BY-SA 4.0 license;
see the [attribution](workloads/README.md#attribution-for-squad-short-qa-material).

Review all passages and answers in
[short_qa_review.md](workloads/tasks/v1/short_qa_review.md).

### Long-context QA: 10 document lookups

These original fictional documents comprise three project registers, three
shipment registers, two equipment registers, and two incident registers. A task
asks for one labeled field of a uniquely identified record among similarly
formatted distractors. Target records appear near the beginning, middle, or end.

Documents contain 653–1,311 words. Complete prompts, including system text and
ChatML formatting, contain **1,803–3,425 upstream Qwen tokens**. Each leaves at
least 128 tokens of margin after the 32-token output allowance under a 4,096-token
limit. The pinned tokenizer revision/checksum are stored in the records; deployed
GGUF tokenization and context fit still need verification.

Each task uses one model call and no tools: the entire document is already in
the prompt. There is no retrieval service or document-reading tool in this
family. The controlled lookup design is RULER-inspired; these are not downloaded
RULER tasks. Score exact answers after stripping surrounding whitespace, keeping
case and punctuation significant: `WH-123` and `WH123` are different answers.

Review full documents and references in
[long_context_review.md](workloads/tasks/v1/long_context_review.md).

### Long generation: 10 explanations and stories

Five tasks request technical explanations about DNS, database indexes, HTTP
caching, Python sorting, and native C compilation. Five request stories set at
a lighthouse, a lunar greenhouse, a railway station, a forest journey, and a
baking contest. All use one model call and no tools; technical source notes are
for evaluation and are not supplied to the serving model.

Inputs are 146–181 upstream Qwen tokens. Five tasks request 200–280 words with
a 512-token cap; five request 450–600 words with a 1,024-token cap. Both groups
mix explanations and stories. Temperature is 0 and EOS is respected, so these
are maximum token budgets, not forced output lengths. Pilot outputs must verify
that the requested word ranges fit the caps before comparative experiments.

Each task has four public content requirements and seven rubric criteria scored
0/1/2. A passing response needs valid execution, at least 12/14, at least 1 on
every criterion, full correctness/consistency credit, the requested word range,
and no listed critical failure. Words are counted with `len(text.split())` over
the entire response. Initial scoring can be human review; an optional fixed LLM
judge can later score saved outputs outside the timed serving experiment.
Rubrics exist; automated judging and rubric-score aggregation are not connected.

Review prompts, rubrics, and reference notes in
[long_generation_review.md](workloads/tasks/v1/long_generation_review.md).

### Multistep: 40 tasks with tool results

| Subtype | Tasks | Tool data and reasoning | Examples of variation |
|---|---:|---|---|
| Sales analysis | 10 | Read regional sales, targets, or period comparisons; calculate the requested summary | Refunds, negative net sales, alphabetical ties, target shortfalls, all-negative period changes |
| Log investigation | 10 | Read log bundles and follow explicit `cause_event_id` links from a starting event | Different origin components, shuffled events, unrelated events with the same request ID |
| Document lookup | 10 | Read document sections or policy/checklist excerpts | Follow section references, choose the highest revision effective by a date, combine approval requirements |
| Inventory check | 10 | Read item or warehouse stock and incoming shipments | Reserved/damaged stock, warehouse pooling, exact balances, no shortages, ties, inclusive delivery deadlines |

**Every subtype** has three tasks with 2 tools, four with 4 tools, and three with
7 tools. Those require 3, 5, and 8 model calls respectively. For example, a
two-tool task follows this sequence:

```text
Model response → tool result 1 → model response → tool result 2 → final model answer
```

Tool order and arguments are scripted in the task records. Each tool returns a
fixed fixture, revealed only when that step executes, with a default two-second
added delay that can be varied independently. The intended runner retains all
previous model responses and tool results. Wrong intermediate answers should
be recorded while the remaining prescribed steps continue; tool exceptions are
execution failures. This measures dependent requests and context growth, not
autonomous tool selection. The fixture-executing runtime is still pending.

Every model response has a 128-token cap with natural EOS. Estimated peak context
budgets range from 835 to 2,275 tokens, including allowances for previous replies,
the current output, and a 128-token margin. These are estimates because actual
model history is not yet available. Final reference answers are typed JSON;
whitespace and object-key order do not matter, extra fields fail, and arrays must
follow the requested order. Reference calculations and fixture validation are
implemented; scoring actual saved model answers is still pending.

Review every workflow, tool result, and reference in
[multistep_review.md](workloads/tasks/v1/multistep_review.md).

## Validation, completion, and accuracy

Run the offline checks from the repository root; no serving model is required:

```bash
python -m workloads.validate_collection
python -m unittest discover -s tests -v
```

The collection validator checks 80 unique IDs, family/subtype counts, answer
spans, rubric structure, multistep reference calculations, call counts, and
manifest checksums. These checks do not measure model accuracy or prove every
question is unambiguous. Read the review files and flag issues by task ID.
After an intentional dataset edit, update its readable copy and refresh the
manifest with `python -m workloads.validate_collection --write-manifest`.
Keep the task version unchanged across scheduler comparisons.

Execution and quality are separate:

| Measure | Definition |
|---|---|
| Completion rate | Validly completed tasks / all offered tasks |
| Accuracy among completed | Correct or quality-passing completed tasks / validly completed tasks |
| Overall success rate | Correct or quality-passing completed tasks / all offered tasks |
| Completed-task throughput | Validly completed tasks / experiment duration |
| Correct-task throughput | Correct or quality-passing completed tasks / experiment duration |

The offline QA scorer requires status `ok`, all planned steps completed, a
terminal completion message, nonempty output, and no context truncation. Missing
tasks and failures remain in the offered-task denominator. Reaching an output
cap alone establishes neither correctness nor sufficient writing quality.

[evaluation/score_qa.py](evaluation/score_qa.py) implements the QA metrics against
saved predictions; see [evaluation/README.md](evaluation/README.md) for the schema
and commands. It does not score multistep JSON or long-generation rubrics.
The existing performance runner's completion counts use a less strict definition:
response capture, natural-EOS settings, and reliable terminal/truncation checks
still need integration. Current test results are software checks, not Qwen accuracy.

## Existing synthetic runner and experiment controls

[workloads/generate.py](workloads/generate.py) is the earlier seeded filler-text
generator. Its output is accepted by the existing runner; **the fixed JSONL task
collection above is not directly accepted yet**. The synthetic generator has
five shapes: `short_qa`, `long_context`, `long_gen`, `multistep`, and `shared_doc`,
mixed by default at 35/15/15/25/10%. `shared_doc` tests prefix reuse over shared
documents; it is not a fifth family in the fixed collection or collaborating agents.

Existing controls include batch, steady, Poisson, and bursty arrivals; unique,
short shared, and long shared prefixes; context/output size; step count; tool
delay; tool-result size; and scheduler concurrency `K`. Filler lengths are
approximate, and the default long shared system prefix adds substantial input.
The current client forces `ignore_eos=true` to exercise output budgets; actual
token counts and failures still need checking. Fixed tasks instead specify
natural EOS and task-specific quality rules.

For the fixed collection, vary arrival schedules, `K`, and tool delays separately
from task content. Creating controlled context-length or response-length sweeps
requires versioned task variants; this 80-task mixed set alone does not isolate
each effect. Multi-agent cooperation is not implemented by either workload path.

### Run a synthetic smoke experiment on the GPU node

```bash
bash setup/setup_node.sh
PY=~/llmsys/venv/bin/python
$PY workloads/generate.py --name mixed --n-tasks 100 --arrival poisson --rate 0.5
CTX=16384 NP=4 bash setup/launch_server.sh --cache-ram 0
$PY -m runner.run --workload workloads/generated/mixed.jsonl \
    --sched fifo_request -k 4 --name my_run \
    --server-args "-c 16384 -np 4 --cache-ram 0"
```

The generated mix can exceed per-slot context capacity, as the pilot did. Check
prompt plus output budgets before a fit-controlled experiment. `--server-args`
records flags; it does not configure the server. Restart between policy runs or
apply an identical documented warm-cache procedure. Use distinct run names to
preserve measurements, and stop the EC2 instance when finished.

## Measurements and their limits

The runner writes [results/raw/](results/raw/) with one subdirectory per run:

| File | Contents |
|---|---|
| `summary.json` | Completed/failed counts, failure rate, p50/p95/p99 successful-task latency, request queueing and TTFT, task/token throughput, cache reuse, peak GPU memory and server RSS, per-type breakdown |
| `tasks.csv` | Per-task completion time, admission wait, cumulative queue/model/tool time, steps completed, generated tokens, status |
| `requests.csv` | Per-call queueing, TTFT, latency, computed/cached/generated tokens, prefill/decode timing, slot, errors, stop type, context truncation |
| `memory.csv` | Device GPU memory/utilization and llama-server RSS, sampled every 100 ms by default |
| `metrics.csv` | llama-server `/metrics`, polled every second |
| `config.json` | Run arguments, recorded server flags/properties, workload metadata, Git commit |

Request TTFT starts at application dispatch and excludes application queue time.
Server-side waiting is included in the observed model-call duration. Task FIFO
reports zero request-queue time because its waiting occurs at admission; compare
total task queueing as well. Latency percentiles exclude failed tasks, so report
failure counts alongside them. Memory sampling does not include runner-process
RSS, and scheduler overhead is not separately isolated. Natural-EOS output length
and semantic quality require the new evaluation path rather than treating every
output below its maximum as a failure.

## Preliminary pilot results

These are **the earlier 30 synthetic tasks**, one seed, `K=4`, `NP=4`,
`CTX=16384`; they are not results for the new 80-task collection.

| Configuration | Completed | Task p50 / p95 (s) | Tasks/s | Peak GPU memory (MiB) | Peak server RSS (MiB) |
|---|---:|---:|---:|---:|---:|
| Cache RAM 0, request FIFO | 26/30 | 12.5 / 50.1 | 0.2688 | 5,916.9 | 867.7 |
| Cache RAM 0, task FIFO | 26/30 | 19.2 / 40.2 | 0.2798 | 5,916.9 | 869.3 |
| Cache RAM 8192, request FIFO | 26/30 | 12.9 / 51.7 | 0.2643 | 5,924.9 | 2,047.8 |
| Cache RAM 8192, task FIFO | 26/30 | 18.1 / 39.3 | 0.2925 | 5,924.9 | 3,144.1 |

All four failures in each run are HTTP 400 context-limit rejections: long-context
prompts exceed the 4,096-token per-slot limit. They do not demonstrate system
RAM or GPU out-of-memory failures. Nearly constant GPU memory in these runs also
does not establish that every form of runtime memory is fixed at startup.

[scripts/pilot.sh](scripts/pilot.sh) restarts the server for each cache setting,
then runs request FIFO followed by task FIFO on that same server. Task FIFO
therefore inherits cache state from the identical workload. In the RAM-cache
case, its initial RSS is about 2,163 MiB versus 848 MiB for request FIFO. These
runs cannot isolate policy or cache benefits; the script still needs per-policy
restarts or a common warm-cache procedure. It also sets `NP=K`, which must be
accounted for when sweeping concurrency.

The recorded medians and tails suggest a tradeoff worth retesting, not a settled
winner. Mean sampled GPU utilization is about 88–95% across these runs, so the
old claim that slow arrivals left the GPU underutilized is not established by
these measurements. The dominant memory bottleneck and saturation point still
require controlled sweeps.

## Next experiments

1. Integrate canonical tasks with the runner: hide reference metadata, reveal
   fixtures one step at a time, respect generation settings, save outputs and
   completion flags, and connect quality scoring.
2. Verify all task budgets with the deployed GGUF runtime and run a small
   correctness pilot. Check long-generation word ranges and multistep history
   growth using actual responses before freezing the task version.
3. Equalize cache state across policies, keep server configuration controlled,
   and compare FIFO policies across K, context/output lengths, tool delays,
   arrival rates, and workload mixes. Repeat runs and choose the best fixed K
   on development workloads.
4. Plot concurrency versus throughput/memory/failures, context versus
   memory/latency, tool delay versus completion time, output length versus
   latency/throughput, and task type versus queueing. Track long-task delays,
   all offered-task outcomes, actual outputs, and policy overhead.
5. Use those measurements to choose one memory-aware mechanism and compare
   against both FIFO and the tuned fixed-concurrency baseline, including cases
   with little benefit. If cache-aware, also compare with a simple fixed cache
   policy using only controls and measurements exposed by the runtime.

## Repository map

| Path | Purpose |
|---|---|
| [setup/](setup/) | GPU-node setup, model download, server launcher, smoke test |
| [workloads/tasks/v1/](workloads/tasks/v1/) | Fixed 80-task definitions, readable copies, manifest |
| [workloads/](workloads/) | Fixed-task builders/validators and the earlier synthetic generator |
| [scheduler/fifo.py](scheduler/fifo.py) | Request-level and task-level FIFO baselines |
| [runner/](runner/) | Synthetic replay client and performance instrumentation |
| [evaluation/](evaluation/) | Offline QA scoring and quality-evaluation contract |
| [tests/](tests/) | QA scoring and multistep reference checks |
| [scripts/pilot.sh](scripts/pilot.sh) | Earlier pilot orchestration, with the cache-state limitation above |
| [results/](results/) | Environment snapshots and raw pilot measurements |
