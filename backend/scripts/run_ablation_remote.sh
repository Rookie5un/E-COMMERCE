#!/usr/bin/env bash
set -euo pipefail

# Sync project to remote server and run ablation experiments there.
# Fill your server settings via env vars (especially SERVER_HOST).
#
# Example:
#   SERVER_USER=root \
#   SERVER_HOST=YOUR_SERVER_IP \
#   SERVER_PORT=22 \
#   REMOTE_PROJECT_DIR=~/E-commerce \
#   EXPERIMENT_NAME=ablation_server_v1 \
#   bash backend/scripts/run_ablation_remote.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

SERVER_USER="${SERVER_USER:-root}"
SERVER_HOST="${SERVER_HOST:-YOUR_SERVER_IP}"
SERVER_PORT="${SERVER_PORT:-22}"
REMOTE_PROJECT_DIR="${REMOTE_PROJECT_DIR:-~/E-commerce}"

# Passed through to remote run script
EXPERIMENT_NAME="${EXPERIMENT_NAME:-ablation_$(date +%Y%m%d_%H%M%S)}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
TRAIN_FILE="${TRAIN_FILE:-data/train_balanced_full.csv}"
MODEL_NAME="${MODEL_NAME:-hfl/chinese-roberta-wwm-ext}"
OUTPUT_ROOT="${OUTPUT_ROOT:-data/experiments}"
LOG_ROOT="${LOG_ROOT:-logs/ablation}"
SEEDS="${SEEDS:-42 2024 3407}"
EPOCHS="${EPOCHS:-5}"
BATCH_SIZE="${BATCH_SIZE:-32}"
MAX_LENGTH="${MAX_LENGTH:-256}"
LEARNING_RATE="${LEARNING_RATE:-2e-5}"
TEST_SIZE="${TEST_SIZE:-0.2}"
WARMUP_RATIO="${WARMUP_RATIO:-0.1}"
WEIGHT_DECAY="${WEIGHT_DECAY:-0.01}"
PATIENCE="${PATIENCE:-3}"

if [[ "${SERVER_HOST}" == "YOUR_SERVER_IP" ]]; then
  echo "ERROR: set SERVER_HOST before running this script." >&2
  exit 1
fi

echo "========================================"
echo "Syncing project to ${SERVER_USER}@${SERVER_HOST}:${REMOTE_PROJECT_DIR}"
echo "========================================"

rsync -az \
  -e "ssh -p ${SERVER_PORT}" \
  --exclude ".git/" \
  --exclude "frontend/node_modules/" \
  --exclude "backend/.venv/" \
  --exclude "backend/venv/" \
  --exclude "backend/venv311/" \
  --exclude "**/__pycache__/" \
  "${REPO_ROOT}/" "${SERVER_USER}@${SERVER_HOST}:${REMOTE_PROJECT_DIR}/"

REMOTE_CMD=$(cat <<REMOTE_EOF
set -euo pipefail
cd ${REMOTE_PROJECT_DIR}/backend
PYTHON_BIN='${PYTHON_BIN}' \\
TRAIN_FILE='${TRAIN_FILE}' \\
MODEL_NAME='${MODEL_NAME}' \\
OUTPUT_ROOT='${OUTPUT_ROOT}' \\
LOG_ROOT='${LOG_ROOT}' \\
EXPERIMENT_NAME='${EXPERIMENT_NAME}' \\
SEEDS='${SEEDS}' \\
EPOCHS='${EPOCHS}' \\
BATCH_SIZE='${BATCH_SIZE}' \\
MAX_LENGTH='${MAX_LENGTH}' \\
LEARNING_RATE='${LEARNING_RATE}' \\
TEST_SIZE='${TEST_SIZE}' \\
WARMUP_RATIO='${WARMUP_RATIO}' \\
WEIGHT_DECAY='${WEIGHT_DECAY}' \\
PATIENCE='${PATIENCE}' \\
bash scripts/run_ablation_experiments.sh
REMOTE_EOF
)

echo "========================================"
echo "Running experiments on remote server"
echo "========================================"
ssh -p "${SERVER_PORT}" "${SERVER_USER}@${SERVER_HOST}" "${REMOTE_CMD}"

echo ""
echo "Remote run finished."
echo "To summarize on remote:"
echo "  cd ${REMOTE_PROJECT_DIR}/backend"
echo "  ${PYTHON_BIN} scripts/collect_ablation_results.py --run_root ${OUTPUT_ROOT}/${EXPERIMENT_NAME}"
