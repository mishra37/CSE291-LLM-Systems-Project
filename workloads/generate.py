"""Deterministic workload generator for agent-serving experiments.

Each output line is one agent task:
{
  "task_id": "mixed-s0-0007",
  "type": "multistep",          # short_qa | long_context | long_gen | multistep | shared_doc
  "arrival_s": 3.21,            # offset from experiment start
  "prefix_group": "long_shared",  # tasks in the same group start with an identical system prompt
  "system": "...",              # system prompt = the shareable prefix
  "steps": [                    # dependent model calls, executed in order
    {"tool_delay_s": 0.0, "user": "...", "max_tokens": 96},
    {"tool_delay_s": 2.0, "user": "[tool:search] ...", "max_tokens": 64}
  ],
  "est_peak_context": 3120      # approx max tokens the task's context reaches, incl. outputs
}
Step 0's "user" is the task. Later steps' "user" is a tool result that the runner
appends after the model's previous reply (after sleeping tool_delay_s), so the
context grows every step. Token counts here are estimates (~1.3 tokens/word);
the runner logs exact counts reported by llama.cpp.

Usage:
  python workloads/generate.py --name mixed --n-tasks 200 --arrival poisson --rate 0.5
  python workloads/generate.py --name ctx4k --mix long_context=1 --ctx-tokens 4000 --arrival batch
  python workloads/generate.py --name delay5 --mix multistep=1 --tool-delay 5 --steps 6
  python workloads/generate.py --name agentdoc8k --mix multistep=1 --doc-tokens 8000 --steps 5
"""
import argparse
import json
import random
import subprocess
from collections import Counter
from pathlib import Path

TOKENS_PER_WORD = 1.3
TURN_OVERHEAD = 8  # chat-template tokens per message

VOCAB = """the of and to in is that for it as was with be by on not he this are or his from at
which but have an they you were her she there would their we him been has when who will more no
if out so said what up its about into than them can only other new some could time these two may
then do first any my now such like our over man me even most made after also did many before must
through back years where much your way well down should because each just those people how too
little state good very make world still own see men work long get here between both life being
under never day same another know while last might us great old year off come since against go
came right used take three system data model memory request server cache token queue latency
agent tool result query document section value error file function input output process step
plan check update report table record score user value range limit batch policy""".split()

SHORT_SYSTEM = "You are a helpful assistant. Answer accurately and concisely."
TOOLS = ["search", "python", "read_file", "sql", "http_get", "calculator"]

DEFAULT_MIX = {"short_qa": 0.35, "long_context": 0.15, "long_gen": 0.15,
               "multistep": 0.25, "shared_doc": 0.10}


def text(rng, n_tokens):
    """Pseudo-English filler of roughly n_tokens tokens."""
    n_words = max(1, int(n_tokens / TOKENS_PER_WORD))
    words = [rng.choice(VOCAB) for _ in range(n_words)]
    for i in range(11, n_words, 12):
        words[i] += "."
    return " ".join(words)


def est_tokens(s):
    return int(len(s.split()) * TOKENS_PER_WORD)


def long_system_prompt():
    """~1500-token rules + tool descriptions. Fixed seed so it is identical across workloads."""
    rng = random.Random(1234)
    parts = [SHORT_SYSTEM, "Follow these rules:"]
    parts += [f"Rule {i + 1}: {text(rng, 40)}" for i in range(20)]
    parts.append("You can call these tools:")
    parts += [f"Tool {t}: {text(rng, 110)}" for t in TOOLS]
    return "\n".join(parts)


def pick(rng, override, lo, hi):
    return override if override is not None else rng.randint(lo, hi)


def make_task(rng, kind, args, system, prefix_group, docs):
    out = lambda lo, hi: pick(rng, args.out_tokens, lo, hi)
    if kind == "short_qa":
        steps = [{"tool_delay_s": 0.0, "user": "Question: " + text(rng, rng.randint(40, 150)),
                  "max_tokens": out(32, 96)}]
    elif kind == "long_context":
        doc = text(rng, pick(rng, args.ctx_tokens, 1500, 6000))
        steps = [{"tool_delay_s": 0.0,
                  "user": f"Document:\n{doc}\n\nSummarize the key points of the document.",
                  "max_tokens": out(64, 160)}]
    elif kind == "long_gen":
        steps = [{"tool_delay_s": 0.0, "user": "Write a detailed story about " + text(rng, 60),
                  "max_tokens": out(512, 1024)}]
    elif kind == "multistep":
        n = pick(rng, args.steps, 3, 8)
        task = "Task: " + text(rng, rng.randint(80, 200))
        if args.doc_tokens:  # agent starts from a large document, e.g. a file or codebase it was handed
            task = f"Document:\n{text(rng, args.doc_tokens)}\n\n{task}"
        steps = [{"tool_delay_s": 0.0, "user": task, "max_tokens": out(64, 160)}]
        for _ in range(n - 1):
            delay = args.tool_delay if args.tool_delay is not None else round(rng.uniform(0.5, 5.0), 2)
            tool = rng.choice(TOOLS)
            steps.append({"tool_delay_s": delay,
                          "user": f"[tool:{tool}] " + text(rng, pick(rng, args.tool_tokens, 100, 400)),
                          "max_tokens": out(64, 160)})
    elif kind == "shared_doc":
        k = rng.randrange(len(docs))
        system, prefix_group = f"{SHORT_SYSTEM}\nDocument:\n{docs[k]}", f"doc{k}"
        steps = [{"tool_delay_s": 0.0, "user": "Question about the document: " + text(rng, 40),
                  "max_tokens": out(32, 96)}]
    else:
        raise ValueError(kind)

    peak = est_tokens(system) + TURN_OVERHEAD
    peak += sum(est_tokens(s["user"]) + s["max_tokens"] + 2 * TURN_OVERHEAD for s in steps)
    return {"type": kind, "prefix_group": prefix_group, "system": system,
            "steps": steps, "est_peak_context": peak}


def arrivals(rng, n, args):
    if args.arrival == "batch":
        return [0.0] * n
    if args.arrival == "steady":
        return [i / args.rate for i in range(n)]
    if args.arrival == "poisson":
        t, out = 0.0, []
        for _ in range(n):
            out.append(t)
            t += rng.expovariate(args.rate)
        return out
    if args.arrival == "bursty":  # bursts of burst_size tasks every burst_gap seconds
        return [(i // args.burst_size) * args.burst_gap + rng.uniform(0, 0.5) for i in range(n)]
    raise ValueError(args.arrival)


def parse_mix(s):
    if not s:
        return DEFAULT_MIX
    mix = {k: float(v) for k, v in (kv.split("=") for kv in s.split(","))}
    unknown = set(mix) - set(DEFAULT_MIX)
    if unknown:
        raise SystemExit(f"unknown task types: {unknown}")
    return mix


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--name", required=True)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n-tasks", type=int, default=100)
    ap.add_argument("--mix", default="", help="e.g. short_qa=0.5,multistep=0.5 (default: mixed)")
    ap.add_argument("--arrival", choices=["batch", "steady", "poisson", "bursty"], default="poisson")
    ap.add_argument("--rate", type=float, default=0.5, help="tasks/s for steady and poisson")
    ap.add_argument("--burst-size", type=int, default=16)
    ap.add_argument("--burst-gap", type=float, default=30.0)
    ap.add_argument("--prefix", choices=["unique", "short_shared", "long_shared"], default="long_shared",
                    help="system prompt sharing (shared_doc tasks always share their document)")
    # sweep knobs: fix a dimension instead of sampling it
    ap.add_argument("--ctx-tokens", type=int, help="long_context document size")
    ap.add_argument("--out-tokens", type=int, help="max_tokens for every step")
    ap.add_argument("--steps", type=int, help="multistep step count")
    ap.add_argument("--tool-delay", type=float, help="seconds per tool call")
    ap.add_argument("--tool-tokens", type=int, help="tokens per tool result")
    ap.add_argument("--doc-tokens", type=int, help="multistep: prepend a document of this size to step 0")
    ap.add_argument("--n-docs", type=int, default=4, help="distinct documents for shared_doc")
    ap.add_argument("--out-dir", default=str(Path(__file__).parent / "generated"))
    args = ap.parse_args()

    rng = random.Random(args.seed)
    mix = parse_mix(args.mix)
    docs = [text(random.Random(5000 + i), 3000) for i in range(args.n_docs)]
    shared = {"short_shared": SHORT_SYSTEM, "long_shared": long_system_prompt()}

    kinds = rng.choices(list(mix), weights=list(mix.values()), k=args.n_tasks)
    times = arrivals(rng, args.n_tasks, args)
    tasks = []
    for i, (kind, t) in enumerate(zip(kinds, times)):
        if args.prefix == "unique":  # unique tokens at the very start defeat prefix caching
            system, group = f"Session {rng.getrandbits(64):016x}. {SHORT_SYSTEM}", f"u{i}"
        else:
            system, group = shared[args.prefix], args.prefix
        task = make_task(rng, kind, args, system, group, docs)
        tasks.append({"task_id": f"{args.name}-s{args.seed}-{i:04d}", "arrival_s": round(t, 3), **task})

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{args.name}.jsonl"
    with open(path, "w") as f:
        for task in tasks:
            f.write(json.dumps(task) + "\n")

    try:
        commit = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    except OSError:
        commit = ""
    peaks = sorted(t["est_peak_context"] for t in tasks)
    meta = {"args": vars(args), "git_commit": commit, "n_tasks": len(tasks),
            "types": Counter(t["type"] for t in tasks),
            "total_steps": sum(len(t["steps"]) for t in tasks),
            "est_peak_context": {"p50": peaks[len(peaks) // 2], "max": peaks[-1]},
            "duration_s": max(times) if times else 0}
    (out_dir / f"{args.name}.meta.json").write_text(json.dumps(meta, indent=2))
    print(f"wrote {path}")
    print(json.dumps({k: meta[k] for k in ("types", "total_steps", "est_peak_context", "duration_s")}))


if __name__ == "__main__":
    main()
