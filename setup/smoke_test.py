"""Smoke test for a running llama-server: checks generation, prefix-cache reuse,
the /slots and /metrics endpoints, and GPU memory. Stdlib only.

Usage: python setup/smoke_test.py [--port 8080]
"""
import argparse
import json
import subprocess
import time
import urllib.request


def post(url, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)


def get(url):
    with urllib.request.urlopen(url, timeout=30) as r:
        return r.read().decode()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8080)
    base = f"http://127.0.0.1:{ap.parse_args().port}"

    print("health:", get(f"{base}/health"))

    # Long shared prefix, sent twice: the 2nd call should report most prompt tokens as cached.
    prefix = "You are a careful assistant. " + "Rule: answer concisely and cite the step. " * 200
    for i in range(2):
        t0 = time.time()
        r = post(f"{base}/completion", {
            "prompt": prefix + f"\nQuestion {i}: what is 17 * {i + 3}?\nAnswer:",
            "n_predict": 64, "cache_prompt": True, "temperature": 0,
        })
        t = r["timings"]
        print(f"call {i}: wall={time.time() - t0:.2f}s prompt_n={t['prompt_n']} "
              f"cache_n={t.get('cache_n')} prompt_ms={t['prompt_ms']:.0f} "
              f"decode_tok/s={t['predicted_per_second']:.1f} slot={r.get('id_slot')}")
    print("output:", r["content"].strip()[:200])

    try:
        slots = json.loads(get(f"{base}/slots"))
        print("slots:", [(s["id"], s.get("n_ctx")) for s in slots])
    except Exception as e:
        print("slots endpoint unavailable:", e)

    metrics = [l for l in get(f"{base}/metrics").splitlines() if l.startswith("llamacpp:")]
    print("metrics:\n  " + "\n  ".join(metrics))

    print(subprocess.run(["nvidia-smi", "--query-gpu=memory.used,memory.total", "--format=csv"],
                         capture_output=True, text=True).stdout)


if __name__ == "__main__":
    main()
