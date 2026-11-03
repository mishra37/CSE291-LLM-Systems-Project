# Memory-aware scheduling for agent workloads on llama.cpp

CSE 291 (LLM Systems) project. Phase 1: a reproducible FIFO baseline, workload definitions,
measurements, and an explanation of the dominant memory bottleneck when serving multi-step
agent tasks on a single GPU.

**Setup:** AWS g6.xlarge (1× NVIDIA L4, 24 GB) · llama.cpp `llama-server` (CUDA) ·
Qwen2.5-7B-Instruct Q4_K_M · exact versions in [results/env_*.txt](results/).

## Repo layout
| Path | What it is |
|---|---|
| [setup/](setup/) | One-shot node setup (build llama.cpp, download model), server launcher, smoke test. See [setup/README.md](setup/README.md). |
| [workloads/generate.py](workloads/generate.py) | Deterministic workload generator (seeded). |
| [scheduler/fifo.py](scheduler/fifo.py) | Baseline schedulers: `fifo_request` (at most K model calls at once; a task gives up its slot while it waits on a tool) and `fifo_task` (at most K tasks at once; a task keeps its slot until it finishes). |
| [runner/](runner/) | Replays a workload against llama-server and records measurements. |
| [scripts/](scripts/) | Experiment scripts (pilot, sweeps). |
| [results/raw/](results/raw/) | One directory per run (CSV + JSON). |

## Key concepts
- **Slot:** llama-server serves `NP` slots in parallel; each holds one sequence and owns
  `CTX / NP` tokens of KV cache (allocated once at startup). Busy slots are batched together
  every decode step.
- **Agent task:** a sequence of dependent model calls separated by tool calls (simulated as
  a sleep + a tool-result message). Context grows every step.
- **Two FIFO baselines** ("fixed concurrency K" can mean two things):
  - `fifo_request`: at most K *model calls* in flight. A task waiting on a tool holds nothing,
    so its slot may be reused and its context recomputed on the next step.
  - `fifo_task`: at most K *tasks* admitted. A task keeps its slot (and KV cache) through tool
    calls, but the slot sits idle during the wait.
- **RAM cache:** when llama.cpp needs a slot for a new request, it doesn't simply throw away
  the old conversation stored there. By default it saves a copy in regular CPU memory (up to
  8 GB, `--cache-ram 8192`), so if that conversation comes back it can be reloaded instead of
  recomputed. We test with this feature both off (`--cache-ram 0`, GPU only) and on.

## Workloads
Five task types, mixed by default (35/15/15/25/10%):

| Type | Shape | Stresses |
|---|---|---|
| `short_qa` | 40–150 tokens in, 32–96 out | baseline |
| `long_context` | 1.5k–6k-token document, 64–160 out | prefill, KV capacity |
| `long_gen` | short prompt, 512–1024 out | decode |
| `multistep` | 3–8 steps, 0.5–5 s tool delays, 100–400-token tool results | context growth, idle KV |
| `shared_doc` | questions over 4 shared 3k-token documents | prefix reuse |

Knobs: arrival (`batch`/`steady`/`poisson`/`bursty`), prefix sharing
(`unique`/`short_shared`/`long_shared`), and fixed values for context length, output length,
step count, tool delay, tool-result size. Prompts are synthetic filler text and output length is
fixed (`ignore_eos`), so runs are comparable and no run can "win" by generating less. Same seed
gives byte-identical workloads; each `.jsonl` has a `.meta.json` with its args.

```bash
python workloads/generate.py --name mixed --n-tasks 100 --arrival poisson --rate 0.5
python workloads/generate.py --name delay5 --mix multistep=1 --steps 6 --tool-delay 5
```

## Running experiments (on the GPU node)
```bash
bash setup/setup_node.sh                      # once per machine
CTX=16384 NP=4 bash setup/launch_server.sh --cache-ram 0
~/llmsys/venv/bin/python -m runner.run --workload workloads/generated/mixed.jsonl \
    --sched fifo_request -k 4 --name my_run --server-args "-c 16384 -np 4 --cache-ram 0"
bash scripts/pilot.sh                         # 4-run pilot, ~25 min
```
Use `tmux` for long runs, and **stop the EC2 instance when done**.

## Results format (`results/raw/<run>/`)
| File | Contents |
|---|---|
| `summary.json` | completed/failed tasks, p50/p95/p99 task latency, queueing, TTFT, throughput, prefix-cache hit ratio, peak GPU memory, per-type breakdown |
| `tasks.csv` | per task: latency split into queue / model / tool time, status |
| `requests.csv` | per model call: queue time, TTFT, latency, prompt tokens computed vs reused from cache, generated tokens, slot |
| `memory.csv` | GPU memory/utilization and server RSS every 100 ms |
| `metrics.csv` | llama-server `/metrics` every second |
| `config.json` | run args, server flags, workload meta, git commit |

## Findings so far (pilot: 30 mixed tasks, K=4, CTX=16384, 1 seed)
| | GPU-only `fifo_request` | GPU-only `fifo_task` | RAM-cache `fifo_request` | RAM-cache `fifo_task` |
|---|---|---|---|---|
| Completed | 26/30 | 26/30 | 26/30 | 26/30 |
| Task latency p50 / p95 | 12.5 / 50.1 s | 19.2 / 40.2 s | 12.9 / 51.7 s | 18.1 / 39.3 s |
| `short_qa` p50 | 5.4 s | 10.1 s | 5.4 s | 9.1 s |
| `multistep` p95 | 55.4 s | 46.1 s | 56.7 s | 43.4 s |
| Context recomputed after tool calls | 36% | 10% | 28% | 10% |
| Peak GPU memory | 5.9 GB | 5.9 GB | 5.9 GB | 5.9 GB |
| Server RSS | 0.9 GB | 0.9 GB | 2.0 GB | 3.1 GB |

1. **Each FIFO version slows down a different kind of task.**
   - With `fifo_request`, a multi-step task goes back to the end of the line after every tool
     call, so long agent tasks end up the slowest.
   - With `fifo_task`, short tasks wait about twice as long, because slots are reserved by
     agent tasks that are just sitting idle while waiting on a tool.
2. **Redoing work after a tool call costs less than waiting in line, for now.** When a task's
   slot gets reused, the model has to re-read the whole conversation, which takes about 0.3 s
   per step at our ~3k-token conversation sizes. Time spent waiting in the queue is much
   larger. We expect this to flip with longer conversations (8k–16k tokens).
3. **llama.cpp's RAM cache helps a little.** Saving old conversations in CPU memory cut the
   amount of redone work from 36% to 28%, at the cost of up to 2 GB extra CPU memory.
4. **GPU memory use doesn't change, so memory pressure shows up in other ways.** llama.cpp
   reserves all the memory it will use at startup, so the GPU always shows 5.9 GB. Running out
   of memory looks like:
   - **Rejected tasks:** each slot can hold only 4,096 tokens, so all 4 failures were long
     documents (5k+ tokens) that didn't fit, even though most of the total 16k-token space was
     unused at the time.
   - **Redone work** when a slot is reused.
   - **Reserved slots sitting idle** during tool calls.
5. **The GPU wasn't fully busy.** Tasks arrived slowly (one every 2 s on average), so the next
   experiments need to send work faster to find the real limits.


