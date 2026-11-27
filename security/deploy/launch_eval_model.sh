#!/usr/bin/env bash
# Launch a Piccolo checkpoint for AISecurity text evaluation on a 24GB A10.
#
# Unlike the 0.8B launcher this keeps chunked prefill enabled and limits
# concurrency, so a 4B/9B model does not OOM on a long V5 prompt.
set -euo pipefail

MODEL=${1:?usage: launch_eval_model.sh MODEL_PATH GPU PORT [BACKEND] [CONTEXT]}
GPU=${2:-0}
PORT=${3:-18616}
BACKEND=${4:-flashinfer}
CONTEXT=${5:-65536}
SERVED=${SERVED:-piccolo-eval}

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
  --chunked-prefill-size "${CHUNKED_PREFILL_SIZE:-2048}" \
  --disable-custom-all-reduce \
  --mamba-full-memory-ratio 0.4 \
  --kv-cache-dtype auto \
  --mamba-ssm-dtype float32 \
  --mamba-radix-cache-strategy extra_buffer_lazy \
  --mem-fraction-static "${MEM_FRACTION_STATIC:-0.50}" \
  --max-running-requests "${MAX_RUNNING_REQUESTS:-8}" \
  --disable-cuda-graph \
  --skip-server-warmup
