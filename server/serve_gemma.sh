#!/usr/bin/env bash
# Launch the llm-scaler vLLM container serving a Gemma 4 model on the B70.
# Usage: ./serve_gemma.sh [model-id] [extra vllm args...]
# Default: the 26B-A4B MoE (4B active params -> fast thinking) from Google's
# QAT bf16 weights, online-quantized to int4 (the grid the QAT trained for).
# Dense alternative: ./serve_gemma.sh google/gemma-4-31B-it-qat-w4a16-ct
# VLLM_OFFLOAD_WEIGHTS_BEFORE_QUANT: llm-scaler README 4.2 — avoids OOM while
# online-quantizing checkpoints larger than VRAM (the 26B-A4B bf16 is 48GiB).
# Host prereq: vm.overcommit_memory=1 (mmap of the 50GB shard fails under the
# default heuristic on a 30GB-RAM box).
#
# Context window: MAXLEN sets --max-model-len. Two ceilings — the model's native
# 262144 (256k) and the VRAM KV pool. The KV pool is sized by gpu-mem-util, NOT
# by MAXLEN, so raising MAXLEN within the pool is ~free VRAM-wise; it only caps
# tokens-per-request. Measured pool (MoE 26B sym_int4, mem-util 0.9): 126,538
# tokens ("GPU KV cache size" in the log). Policy = half of the binding max so a
# single request can never exhaust the pool: 126538/2 ~= 63000. RE-DERIVE per
# model — the 31B fallback loads bigger weights -> smaller KV pool -> lower half.
# VLLM_ALLOW_LONG_MAX_MODEL_LEN permits MAXLEN above the config-derived cap.
# Thinking transcript: --reasoning-parser gemma4 alone now recovers
# reasoning_content (vLLM PR #39027, present in this build: the parser's
# adjust_request() sets skip_special_tokens=False). No extra flag needed; the
# harness passes chat_template_kwargs {"enable_thinking":true} per request.
set -euo pipefail
MODEL="${1:-google/gemma-4-26B-A4B-it-qat-q4_0-unquantized}"
shift || true
EXTRA="$*"
if [ -z "$EXTRA" ]; then
  case "$MODEL" in
    # Base -it models: online quant per llm-scaler README 3.3 (the DOCUMENTED,
    # Intel-tested path). fp8 = 8-bit, higher quality; override with
    # `--quantization sym_int4 --dtype float16` for 4-bit. The QAT variants
    # (w4a16-ct, q4_0-unquantized) hit untested kernels — k_descale / moe_topk.
    *-it) EXTRA="--quantization fp8 --dtype float16 --mamba-ssm-cache-dtype float16 --block-size 64" ;;
    *q4_0-unquantized*) EXTRA="--quantization sym_int4 --dtype float16" ;;
  esac
fi
# MAXLEN two roles: (1) SERVE ceiling = --max-model-len, set ~95% of the KV pool
# (free VRAM-wise, just caps per-request); (2) the harness's FEED target is a
# separate ~half-of-pool discipline enforced in prompt-building, not here.
# Pools measured @ mem-util 0.9: 31B=38,302 (95%~=36000); MoE=126,538 (unusable).
# RE-DERIVE per model from "GPU KV cache size" in the log. Env-overridable.
MAXLEN="${MAXLEN:-36000}"
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
  -e VLLM_OFFLOAD_WEIGHTS_BEFORE_QUANT=1 \
  -e VLLM_ALLOW_LONG_MAX_MODEL_LEN=1 \
  -e VLLM_WORKER_MULTIPROC_METHOD=spawn \
  -e ZE_AFFINITY_MASK=0 \
  --entrypoint bash "$TAG" \
  -c "vllm serve '$MODEL' --port 8000 --max-model-len $MAXLEN --served-model-name gemma --reasoning-parser gemma4 $EXTRA 2>&1 | tee /llm/models/serve.log"

echo "container started: docker logs -f vllm"
