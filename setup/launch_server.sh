#!/usr/bin/env bash
# Start llama-server in the background. KV budget is controlled by CTX (total tokens
# across all slots) and NP (number of parallel slots); each slot gets CTX/NP tokens.
# Usage: CTX=16384 NP=4 bash setup/launch_server.sh [extra llama-server args]
set -euo pipefail

ROOT="${ROOT:-$HOME/llmsys}"
MODEL="${MODEL:-$ROOT/models/Qwen2.5-7B-Instruct-Q4_K_M.gguf}"
CTX="${CTX:-16384}"
NP="${NP:-4}"
PORT="${PORT:-8080}"
LOG="${LOG:-$ROOT/server_${PORT}.log}"

pkill -f "llama-server.*--port $PORT" 2>/dev/null && sleep 1 || true

nohup "$ROOT/llama.cpp/build/bin/llama-server" \
  -m "$MODEL" -c "$CTX" -np "$NP" -ngl 99 \
  --host 127.0.0.1 --port "$PORT" --metrics \
  "$@" > "$LOG" 2>&1 &

echo "llama-server pid $! (ctx=$CTX, slots=$NP, port=$PORT), log: $LOG"
for _ in $(seq 120); do
  curl -sf "http://127.0.0.1:$PORT/health" >/dev/null && { echo "ready"; exit 0; }
  sleep 1
done
echo "server did not become ready; tail of log:"; tail -30 "$LOG"; exit 1
