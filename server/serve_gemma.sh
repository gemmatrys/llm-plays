#!/usr/bin/env bash
# Launch the llm-scaler vLLM container serving a Gemma 4 model on the B70.
# Usage: ./serve_gemma.sh [model-id] [extra vllm args...]
# Default: the 26B-A4B MoE (4B active params -> fast thinking) from Google's
# QAT bf16 weights, online-quantized to int4 (the grid the QAT trained for).
# Dense alternative: ./serve_gemma.sh google/gemma-4-31B-it-qat-w4a16-ct
set -euo pipefail
MODEL="${1:-google/gemma-4-26B-A4B-it-qat-q4_0-unquantized}"
shift || true
EXTRA="$*"
if [ -z "$EXTRA" ]; then
  case "$MODEL" in
    *q4_0-unquantized*) EXTRA="--quantization sym_int4 --dtype float16" ;;
  esac
fi
TAG=intel/llm-scaler-vllm:0.21.0-b1

docker rm -f vllm 2>/dev/null || true
docker run -d --name vllm --restart unless-stopped \
  --device /dev/dri/card0 --device /dev/dri/renderD128 \
  --group-add "$(getent group render | cut -d: -f3)" --shm-size 32g \
  -p 8000:8000 --dns 1.1.1.1 --dns 8.8.8.8 \
  -v /opt/models:/llm/models \
  -e HF_HOME=/llm/models \
  -e HF_TOKEN="$(cat ~/.hf_token)" \
  -e http_proxy= -e https_proxy= -e no_proxy=localhost,127.0.0.1 \
  --entrypoint bash "$TAG" \
  -c "vllm serve '$MODEL' --port 8000 --max-model-len 8192 --served-model-name gemma --reasoning-parser gemma4 $EXTRA 2>&1 | tee /llm/models/serve.log"

echo "container started: docker logs -f vllm"
