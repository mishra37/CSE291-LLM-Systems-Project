# Memory-aware agent serving

This CSE291A project studies how to schedule agent workloads on a memory-limited local LLM server. An agent can make several model requests, pause for tool results, and return with a larger conversation. Phase 1 implements and measures two fixed-concurrency FIFO baselines. Phase 2 will use those measurements to design a memory-aware policy.

The main experiment runs **Qwen2.5-7B-Instruct Q4_K_M through llama.cpp** on one GPU host. Inference uses the local `llama-server` HTTP endpoint; the UCSD/OpenAI-compatible API is not part of the measured serving path.

## How the repository fits together

```text
workloads/tasks/v2/ ──> runner/fixed.py ──> runner/run.py
                                               │
                            scheduler/fifo.py ├──> runner/llama_client.py ──> llama-server
                                               │
                            local tool fixtures┘
                                               │
                               results/raw/<run>/ ──> evaluation/ + analysis/
```

| Path | Responsibility |
|---|---|
| [setup/](setup/) | Build llama.cpp with CUDA, download the GGUF model, create a Python environment, launch and smoke-test the server. |
| [workloads/](workloads/) | Store versioned task definitions, fixture data, builders, validators, and the fixed experiment selection. |
| [scheduler/fifo.py](scheduler/fifo.py) | Implement the two FIFO policies with a concurrency limit `K`. |
| [runner/](runner/) | Load tasks, schedule arrivals and model calls, execute scripted local tools, stream responses, and record timing, memory, and outputs. |
| [evaluation/](evaluation/) | Score QA and final JSON answers; measure writing length while leaving semantic writing quality for review. |
| [scripts/phase1_fifo.py](scripts/phase1_fifo.py) | Run paired FIFO comparisons, restarting the server before **every** run and recording deployment checksums. |
| [scripts/launch_phase1_all.sh](scripts/launch_phase1_all.sh) | Launch the complete Phase 1 matrix sequentially. Use the smaller commands below when starting out. |
| [analysis/](analysis/) | Validate raw runs, aggregate metrics by run and task family, and generate curves. |
| [tests/](tests/) | Check task data, scoring, runner behavior, and scheduler integration. |
| [results/](results/) | Raw run artifacts and generated reports. |

### What the two FIFOs schedule

Both policies serve eligible work in arrival order. `K` limits simultaneous work at the scheduler; `NP` is llama.cpp's server slot count, so use `NP >= K`.

| Policy | Queue unit | During a tool wait | Returning model step |
|---|---|---|---|
| `fifo_request` | Individual model request | Releases scheduler capacity for another request | Joins the request queue again; server KV reuse is not guaranteed. |
| `fifo_task` | Entire agent task | Keeps its admission and assigned server slot idle | Uses the same slot, allowing its context to remain reusable. |

The runner calls each policy through the same `task()` and `request()` interface. In task FIFO, the task obtains a slot ticket before its first model call and returns it after its final step. In request FIFO, `K` workers pull model requests from one queue; a tool wait occupies no worker. See [the runner guide](runner/README.md) for the execution sequence and failure rules.

## Workloads

The checked-in [v2 collection](workloads/tasks/v2/) contains 80 deterministic tasks. A fixed [60-task selection](results/validation_v2_60/selection.json) is used for the main controlled comparison; the remaining 20 are available for additional checks.

| Family | Count | Model and tool pattern | What it exercises |
|---|---:|---|---|
| Short QA | 20 | One model call; no tools | Short input and short answer. Selected from SQuAD 1.1 development data. |
| Long-context QA | 10 | One model call; no tools | Retrieval from an authored document with distractor records. |
| Long generation | 10 | One model call; no tools | Longer response and output-token cost. |
| Multistep | 40 | Several dependent model calls with 2, 4, or 7 scripted tool calls | Growing conversation, tool delay, and context reuse. Sales, logs, document, and inventory scenarios. |

Tool calls use local, fixed fixtures and controlled delays. The model is not asked to choose the next tool. Every later model call receives the prior conversation and the newly revealed tool result. Answer references remain in evaluator data and are not sent to the model. The task sources, construction, schemas, and validation commands are documented in [workloads/README.md](workloads/README.md). The older [v1 tasks](workloads/tasks/v1/) remain available to reproduce exploratory runs.

## Setup and first run

Run these commands from the repository root on a Linux GPU host. The setup script puts the llama.cpp build, model, and virtual environment under `~/llmsys` by default. Its requirements and platform notes are in [setup/README.md](setup/README.md).

```bash
bash setup/setup_node.sh
CTX=16384 NP=4 bash setup/launch_server.sh --cache-ram 0
~/llmsys/venv/bin/python setup/smoke_test.py
```

Check task definitions and run the software tests without using the GPU:

```bash
~/llmsys/venv/bin/python -m workloads.validate_collection
~/llmsys/venv/bin/python -m unittest discover -s tests -v
```

Run two short QA tasks through the live server:

```bash
~/llmsys/venv/bin/python -m runner.run \
  --workload workloads/tasks/v2/short_qa.jsonl --max-tasks 2 \
  --sched fifo_request -k 1 --name short_qa_smoke
```

Run names must be new: the runner refuses to overwrite an existing output directory. Direct `runner.run` calls use the server already running on `127.0.0.1:8080`; they do not restart it between policies. Use the experiment driver below for controlled comparisons.

## Reproduce the controlled FIFO comparison

The committed task definitions are ready to use. Generate the deterministic 60-task selection once, then preview a paired run. The example executes one repeat of each FIFO at `K=2` when `--dry-run` is removed; it does **not** launch the full matrix.

```bash
PY=~/llmsys/venv/bin/python
$PY -m scripts.select_validation
$PY -m scripts.phase1_fifo \
  --workload workloads/generated/validation_v2_60.jsonl \
  --prefix my_phase1_k2 --k 2 --repeats 1 --np 4 --ctx 16384 \
  --cache-ram 0 --dry-run

# After reviewing the planned run names, execute the pair:
$PY -m scripts.phase1_fifo \
  --workload workloads/generated/validation_v2_60.jsonl \
  --prefix my_phase1_k2 --k 2 --repeats 1 --np 4 --ctx 16384 \
  --cache-ram 0
```

`scripts.phase1_fifo` starts a fresh server for each policy/repeat, applies the same one-request warm-up, and writes the model, workload, runtime, and source checksums to `deployment.json`. It refuses to overwrite previous runs. Keep the model and precision fixed, pair policies on the same workload, and keep `NP` and `CTX` fixed while varying `K`. The complete controls and metric definitions are in [the Phase 1 protocol](docs/phase1_protocol.md); the exact core and follow-up sweep commands are in [the experiment matrix](docs/phase1_experiment_matrix.md).

Generate the paired synthetic context and output workloads only when running those sweeps:

```bash
$PY -m workloads.build_phase1_sweeps
```

To summarize and plot completed core runs, use a prefix that exists under `results/raw/`:

```bash
$PY -m analysis.phase1_report --prefix my_phase1_k2 --out results/my_phase1_k2
$PY -m analysis.phase1_core_plots --report results/my_phase1_k2
```

The historical `scripts/pilot.sh`, `scripts/quality.sh`, and `scripts/sweep.sh` reproduce earlier v1 exploration. They are kept separate from the controlled v2 driver and [audited here](docs/v1_sweep_audit.md).

## Measurements and saved artifacts

Each run creates `results/raw/<run-name>/`. The timing window covers the offered workload through its final terminal task state, including queue and tool waits. Results are retained at both model-request and complete-task granularity.

| File | Contents |
|---|---|
| `deployment.json`, `config.json` | Exact model/runtime/source/workload identity and run settings. |
| `offered_tasks.jsonl`, `schedule.jsonl` | Offered task set and planned arrivals/delays, including incomplete tasks. |
| `tasks.csv`, `requests.csv` | Per-task completion and queue times; per-request wait, token counts, cache reuse, and server timing. |
| `memory.csv`, `metrics.csv` | Sampled GPU and server memory plus llama.cpp metrics. |
| `responses.jsonl`, `tools.jsonl` | Model prompts/responses and local tool events. |
| `predictions.jsonl`, `quality.jsonl` | Final answers and per-task scoring or pending writing review. |
| `summary.json` | Offered, completed, failed, latency percentiles, throughput, memory peaks, and quality totals. |

The report scripts produce `runs.csv`, `types.csv`, `repetitions.csv`, and plots. Check completion and failure counts alongside latency and throughput; inspect generated-token counts, truncations, and per-family queue tails before comparing policies. Automatic correctness covers QA and multistep JSON. Writing length is checked automatically; semantic writing quality needs separate review. Full definitions and limits are in [the Phase 1 protocol](docs/phase1_protocol.md).

## Documentation and results

- [Phase 1 protocol](docs/phase1_protocol.md): controlled comparison procedure and metric definitions.
- [Experiment matrix](docs/phase1_experiment_matrix.md): run configurations and reporting commands.
- [Phase 1 measurements](docs/phase1_results.md): detailed results, plots, interpretation, and exploratory v1 observations.
- [56 follow-up sweeps](results/phase1_followup_56/README.md): one detailed Markdown report, all five sweep report sets, and links to every raw run.
- [Phase 1 report draft](docs/phase1_report.tex): writeup and milestone appendix.
- [Generated reports](results/): raw data, per-group CSVs, and curves for the core, tool-delay, arrival-rate, context, output, and RAM-cache sweeps.
