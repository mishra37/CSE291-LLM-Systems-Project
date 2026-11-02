#!/usr/bin/env bash
# One-shot setup for a GPU node (DataHub or AWS g6/g6e).
# Builds llama.cpp with CUDA, downloads the model, creates a Python venv.
# Usage: bash setup/setup_node.sh        (re-running is safe; finished steps are skipped)
set -euo pipefail

ROOT="${ROOT:-$HOME/llmsys}"                     # everything heavy lives here, outside the repo
LLAMA_REF="${LLAMA_REF:-master}"                 # pin a tag/commit once we pick one
MODEL_URL="${MODEL_URL:-https://huggingface.co/bartowski/Qwen2.5-7B-Instruct-GGUF/resolve/main/Qwen2.5-7B-Instruct-Q4_K_M.gguf}"
MODEL_PATH="$ROOT/models/$(basename "$MODEL_URL")"
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
JOBS="$(nproc)"

mkdir -p "$ROOT/models"
echo "== GPU =="
nvidia-smi --query-gpu=name,memory.total,driver_version,compute_cap --format=csv

# ---- toolchain ----------------------------------------------------------------
for d in /usr/local/cuda/bin /usr/local/cuda-*/bin "$ROOT/cuda/bin"; do
  [ -x "$d/nvcc" ] && ! command -v nvcc >/dev/null && export PATH="$d:$PATH"
done
if ! command -v nvcc >/dev/null; then
  # DataHub has no system CUDA toolkit; Blackwell (RTX PRO 6000) needs CUDA >= 12.8
  echo "== nvcc not found: installing CUDA 12.8 toolkit via conda into $ROOT/cuda =="
  conda create -y -p "$ROOT/cuda" -c "nvidia/label/cuda-12.8.1" cuda-toolkit
  export PATH="$ROOT/cuda/bin:$PATH"
fi
CUDA_ROOT="$(dirname "$(dirname "$(command -v nvcc)")")"
nvcc --version | tail -1

if ! command -v cmake >/dev/null; then
  python3 -m pip install --user cmake
  export PATH="$HOME/.local/bin:$PATH"
fi

# ---- llama.cpp ----------------------------------------------------------------
if [ ! -d "$ROOT/llama.cpp" ]; then
  git clone https://github.com/ggml-org/llama.cpp "$ROOT/llama.cpp"
fi
git -C "$ROOT/llama.cpp" fetch -q && git -C "$ROOT/llama.cpp" checkout -q "$LLAMA_REF"
git -C "$ROOT/llama.cpp" pull -q 2>/dev/null || true

# compute_cap "8.9" -> "89" (L4), "12.0" -> "120" (RTX PRO 6000)
ARCH="$(nvidia-smi --query-gpu=compute_cap --format=csv,noheader | head -1 | tr -d '. ')"
if [ ! -x "$ROOT/llama.cpp/build/bin/llama-server" ]; then
  cmake -S "$ROOT/llama.cpp" -B "$ROOT/llama.cpp/build" \
    -DGGML_CUDA=ON -DCMAKE_BUILD_TYPE=Release -DLLAMA_CURL=OFF \
    -DCMAKE_CUDA_ARCHITECTURES="${ARCH:-native}" -DCUDAToolkit_ROOT="$CUDA_ROOT"
  cmake --build "$ROOT/llama.cpp/build" -j "$JOBS" --target llama-server llama-bench
fi

# ---- model --------------------------------------------------------------------
if [ ! -f "$MODEL_PATH" ]; then
  curl -L --fail -o "$MODEL_PATH.part" "$MODEL_URL" && mv "$MODEL_PATH.part" "$MODEL_PATH"
fi

# ---- python -------------------------------------------------------------------
if [ ! -d "$ROOT/venv" ]; then
  python3 -m venv "$ROOT/venv"
fi
"$ROOT/venv/bin/pip" install -q --upgrade pip
"$ROOT/venv/bin/pip" install -q -r "$REPO_DIR/requirements.txt"

# ---- record environment for reproducibility -----------------------------------
ENV_FILE="$REPO_DIR/results/env_$(hostname).txt"
mkdir -p "$REPO_DIR/results"
{
  echo "date: $(date -Is)"
  echo "host: $(hostname)"
  echo "llama.cpp commit: $(git -C "$ROOT/llama.cpp" rev-parse HEAD)"
  echo "model: $MODEL_PATH ($(du -h "$MODEL_PATH" | cut -f1))"
  echo "cuda arch: $ARCH"
  nvcc --version | tail -1
  nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader
  echo "cpus: $JOBS  ram: $(free -g | awk '/Mem:/{print $2}')G"
} | tee "$ENV_FILE"

echo
echo "Setup done. Next:  bash setup/launch_server.sh   then   $ROOT/venv/bin/python setup/smoke_test.py"
