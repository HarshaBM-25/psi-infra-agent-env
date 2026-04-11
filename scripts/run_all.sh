#!/usr/bin/env bash
set -e
echo "========================================"
echo "  InfraAgent-Env v2 — Full Benchmark"
echo "========================================"
export API_BASE_URL=${API_BASE_URL:-"https://router.huggingface.co/v1"}
export MODEL_NAME=${MODEL_NAME:-"Qwen/Qwen2.5-72B-Instruct"}
export ENV_BASE_URL=${ENV_BASE_URL:-"http://localhost:7860"}
curl -sf ${ENV_BASE_URL}/health > /dev/null || {
  echo "ERROR: Server not running at ${ENV_BASE_URL}"
  echo "Start with: uvicorn main:app --host 0.0.0.0 --port 7860"
  exit 1
}
python inference.py
