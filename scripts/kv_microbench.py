"""What does it cost to bring back an agent's KV cache after a tool call?

For each context size N (one slot, nothing else running) this measures, as client wall time:
  recompute    prefill all N tokens from scratch (KV was thrown away)
  gpu_kept     same prompt + a short suffix while the KV is still in GPU memory
  ssd_save     write the slot's KV to a file   (POST /slots/0?action=save)
  ssd_restore  read it back after erasing the slot, then answer prompt + suffix
  ram_restore  the KV was pushed to llama.cpp's host-RAM prompt cache by another prompt,
               then prompt + suffix brings it back            (--mode ram only)
Every trial uses a fresh random prompt so nothing is reused by accident.

  # SSD path: server started with --cache-ram 0 --slot-save-path <dir>
  python scripts/kv_microbench.py --mode ssd --out results/raw/micro_kv/ssd.csv
  # RAM path: server started with --cache-ram 8192
  python scripts/kv_microbench.py --mode ram --out results/raw/micro_kv/ram.csv
Run it through `bash scripts/sweep.sh micro`, which starts the right servers.
"""
import argparse
import csv
import json
import random
import statistics
import subprocess
import time
import urllib.request
from pathlib import Path

WORDS = ("the of and to in is that for it as was with be by on not this are or from at which but have an "
         "they you were her there would their we been has when who will more no if out so said what up its "
         "about into than them can only other new some could time these two may then do first any now such "
         "system data model memory request server cache token queue latency agent tool result query document "
         "section value error file function input output process step plan check update report table").split()


def post(url, body=None, timeout=600):
    req = urllib.request.Request(url, data=json.dumps(body or {}).encode(), method="POST",
                                 headers={"Content-Type": "application/json"})
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=timeout) as r:
        out = json.loads(r.read())
    return out, (time.perf_counter() - t0) * 1000


def tokens(url, n, rng):
    """Exactly n token ids of random text, starting with a unique marker."""
    words = [f"session-{rng.getrandbits(48):012x}:"] + [rng.choice(WORDS) for _ in range(int(n * 1.2) + 16)]
    ids = post(f"{url}/tokenize", {"content": " ".join(words)})[0]["tokens"]
    assert len(ids) >= n, (len(ids), n)
    return ids[:n]


def complete(url, prompt):
    out, ms = post(f"{url}/completion", {"prompt": prompt, "n_predict": 1, "cache_prompt": True,
                                         "id_slot": 0, "temperature": 0})
    return ms, out["timings"]["prompt_n"]


def drop_page_cache():
    """So the restore really reads the SSD instead of the OS file cache (needs passwordless sudo)."""
    return subprocess.run(["sudo", "-n", "sh", "-c", "sync; echo 3 > /proc/sys/vm/drop_caches"],
                          capture_output=True).returncode == 0


def trial(url, mode, n, rng):
    erase = lambda: post(f"{url}/slots/0?action=erase")
    suffix = post(f"{url}/tokenize", {"content": " Now answer briefly."})[0]["tokens"]
    prompt = tokens(url, n, rng)
    erase()
    row = {"n_tokens": n}
    row["recompute_ms"], row["recompute_prompt_n"] = complete(url, prompt)
    row["gpu_kept_ms"], row["gpu_kept_prompt_n"] = complete(url, prompt + suffix)
    if mode == "ssd":
        name = f"micro_{n}_{rng.getrandbits(32):08x}.bin"
        saved, row["ssd_save_ms"] = post(f"{url}/slots/0?action=save", {"filename": name})
        row["kv_bytes"] = saved.get("n_written")
        erase()
        row["page_cache_dropped"] = drop_page_cache()
        _, restore_ms = post(f"{url}/slots/0?action=restore", {"filename": name})
        answer_ms, row["ssd_restore_prompt_n"] = complete(url, prompt + suffix)
        row["ssd_restore_ms"] = restore_ms + answer_ms
        row["ssd_restore_only_ms"] = restore_ms
    else:
        complete(url, tokens(url, n, rng))  # another conversation takes the slot -> ours goes to host RAM
        row["ram_restore_ms"], row["ram_restore_prompt_n"] = complete(url, prompt + suffix)
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default="http://127.0.0.1:8080")
    ap.add_argument("--mode", choices=["ssd", "ram"], required=True)
    ap.add_argument("--sizes", default="1024,2048,4096,8192,16384,30000")
    ap.add_argument("--trials", type=int, default=3)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    complete(args.url, tokens(args.url, 256, rng))  # warm-up
    rows = [dict(trial(args.url, args.mode, int(n), rng), trial=t)
            for n in args.sizes.split(",") for t in range(args.trials)]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(k for r in rows for k in r))
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)

    cols = [k for k in keys if k.endswith("_ms")] + (["kv_bytes"] if args.mode == "ssd" else [])
    print("median of", args.trials, "trials (ms; kv_bytes in MB)")
    print("n_tokens  " + "  ".join(f"{c:>20}" for c in cols))
    for n in args.sizes.split(","):
        sub = [r for r in rows if r["n_tokens"] == int(n)]
        vals = [statistics.median(r[c] for r in sub if r.get(c) is not None) for c in cols]
        vals = [v / 1e6 if c == "kv_bytes" else v for c, v in zip(cols, vals)]
        print(f"{n:>8}  " + "  ".join(f"{v:>20.1f}" for v in vals))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
