#!/usr/bin/env bash
# Launch Piccolo-0.8B-VL for the AISecurity text evaluation.
#
#   bash security/deploy/launch_0_8b.sh /models/Piccolo-0.8B-VL 0 18604 flashinfer 65536
#
# Backends: fa3 (Hopper H100/H200), flashinfer or triton (Ada/Ampere, e.g. L20/L4/A10).
# BF16 is intentional: the baseline must not mix in FP8 or GGUF numerics.
set -euo pipefail

MODEL=${1:?usage: launch_0_8b.sh MODEL_PATH GPU PORT [BACKEND] [CONTEXT]}
GPU=${2:-0}
PORT=${3:-18604}
BACKEND=${4:-flashinfer}
CONTEXT=${5:-65536}
SERVED=${SERVED:-piccolo-0.8b-vl}

export CUDA_VISIBLE_DEVICES="$GPU"
export PYTHONDONTWRITEBYTECODE=1
export SGLANG_PLUGINS=piccolo
export HF_HUB_OFFLINE="${HF_HUB_OFFLINE:-1}"

exec "${PYTHON:-python}" -m sglang.launch_server \
  --model-path "$MODEL" \
  --tokenizer-path "$MODEL" \
  --served-model-name "$SERVED" \
  --host 127.0.0.1 \
  --port "$PORT" \
  --api-key "${PICCOLO_SERVER_KEY:-${PICCOLO_API_KEY:-EMPTY}}" \
  --tp-size 1 \
  --random-seed 42 \
  --trust-remote-code \
  --context-length "$CONTEXT" \
  --dtype bfloat16 \
  --json-model-override-args '{"text_config":{"is_causal":false}}' \
  --attention-backend "$BACKEND" \
  --disable-radix-cache \
  --chunked-prefill-size -1 \
  --disable-custom-all-reduce \
  --mamba-full-memory-ratio 0.4 \
  --kv-cache-dtype auto \
  --mamba-ssm-dtype float32 \
  --mamba-radix-cache-strategy extra_buffer_lazy \
  --mem-fraction-static "${MEM_FRACTION_STATIC:-0.60}" \
  --max-running-requests 64 \
  --skip-server-warmup
