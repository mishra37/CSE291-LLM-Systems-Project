# Executing the fixed tasks

Run commands from the repository root on the machine hosting llama-server.
Install the repository requirements in the Python environment first. No external
tool API or judge service is required. Model inference uses `--url`, defaulting
to `http://127.0.0.1:8080`; it does not use GPT or another cloud inference API.

## First model smoke run

```bash
CTX=16384 NP=4 bash setup/launch_server.sh --cache-ram 0
~/llmsys/venv/bin/python -m runner.run \
  --workload workloads/tasks/v2/short_qa.jsonl --max-tasks 2 \
  --sched fifo_request -k 1 --name v2_short_smoke
```

Choose a new name for every run; nonempty output directories are rejected.
Repeat with a few records from `long_context.jsonl`, `long_generation.jsonl`,
and `multistep.jsonl` to verify real-model behavior before a full replay.

## Whole collection

```bash
~/llmsys/venv/bin/python -m runner.run \
  --workload workloads/tasks/v2 --sched fifo_request -k 4 \
  --arrival batch --tool-delay 2 --name v2_80_request_k4
```

For task FIFO use `--sched fifo_task` and a new name. Restart the server with
the same configuration before each comparison, then use the same runner warm-up
(one short request by default). Keep `NP >= K`. These commands do not themselves
reset caches. `scripts/pilot.sh` remains the earlier synthetic pilot.

The directory loads short QA, long-context QA, long generation, then multistep,
preserving each file's record order. This deterministic order is recorded, but
is not a randomized experimental design. `--max-tasks` selects the first N overall,
not N per family. `--arrival steady --rate 0.5` spaces fixed tasks two seconds
apart. Batch arrivals are the default. The optional `--tool-delay` overrides the
stored two-second delay; zero is useful for software tests. Synthetic files keep
their original arrival schedules and delays.

## How execution works

Version 2 uses 128 tokens for intermediate multistep responses and 256 for final
answers; v1 still uses 128 throughout. The runner honors each stored step cap.

1. `fixed.py` reads the task file and constructs prompts using only the stored
   system instruction and public input. QA receives its passage/document and
   question; writing receives its prompt. Evaluator references are excluded.
2. `run.py` waits for the scheduled arrival and enters the selected scheduler.
   Request FIFO queues each model call; task FIFO admits and pins the entire task.
3. The client calls llama-server's streaming `/completion` endpoint. Fixed tasks
   use their declared temperature, output cap, and natural EOS. Synthetic tasks
   retain their legacy forced-output setting.
4. For multistep tasks, after a successful intermediate response, the runner
   waits the configured tool delay and looks up the prescribed local fixture.
   It records the operation and adds `[tool:name] {result}` plus the next
   instruction as a user message, matching the task builder's budget template.
   All prior user/model messages remain in the next prompt. Only the current
   tool result is revealed. Tool choice is scripted, not chosen by model output.
5. Wrong intermediate content does not stop the workflow. HTTP errors, timeouts,
   missing terminal messages, empty replies, context truncation, or tool errors
   fail execution. Partial responses are preserved. A final JSON answer can be
   incorrect even when execution completes successfully.
6. After the timed replay, QA is scored with the existing normalization rules.
   Multistep JSON requires exact values and types, no extra/duplicate fields,
   and the requested array order. Writing gets word counts and length checks;
   semantic rubric judgment remains explicitly pending, never an automatic pass.

For example, the first sales task makes a planning call, receives North's data,
makes another call, receives South's data, and continues through West and East.
Its fifth model call produces the final answer. With request FIFO, another task
can use request capacity during each tool wait. With task FIFO, the sales task
keeps its admission and slot throughout all five calls and four tool waits.

## Saved artifacts

All output goes to `results/raw/<name>/`. Existing timing CSVs and memory sampling
remain available. Additional files are:

| File | Contents |
|---|---|
| `offered_tasks.jsonl` | Exact offered definitions, including evaluator references; never sent wholesale to the model |
| `schedule.jsonl` | Task arrival times and configured delays per step |
| `responses.jsonl` | Every actual model prompt, response text, status, completion flag, server metadata, and generation settings |
| `tools.jsonl` | Tool name, arguments, result, start/end times, or execution error |
| `predictions.jsonl` | One final/partial response per task with completed-step count and completion/truncation flags |
| `quality.jsonl` | Per-task QA/JSON correctness or writing length compliance and pending judgment |

`summary.json` includes counts of scored-correct tasks and pending writing
judgments. Its throughput and latencies describe execution, not semantic success.
Short natural-EOS responses below their token cap are not automatically failures;
the legacy `short_outputs` field only counts outputs below that cap.

The standalone QA scorer accepts predictions for only its offered QA tasks;
filter the predictions from a mixed run before passing them to that CLI.

## Local verification

```bash
python -m workloads.validate_collection
python -m unittest discover -s tests -v
```

The integration test sends all 80 tasks through both real FIFO implementations
and the HTTP client to a local mock server, checking 252 model requests and 172
tool calls per replay, generation settings, history, result visibility, failure
detection, and saved outputs. It does not measure Qwen accuracy or AWS performance.
Real deployed tokenization/context fit and long-writing rubric review remain
required before comparative measurements. Responses are written at the end of
the run; process-crash recovery and incremental checkpointing are not implemented.
