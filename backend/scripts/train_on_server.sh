#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   bash scripts/train_on_server.sh
#
# Optional environment variables:
#   PYTHON_BIN=python3.11
#   VENV_DIR=.venv
#   TRAIN_FILE=data/train_multiclass.csv
#   OUTPUT_DIR=data/models/roberta-sentiment
#   MODEL_NAME=hfl/chinese-roberta-wwm-ext
#   BATCH_SIZE=16
#   EPOCHS=3
#   MAX_LENGTH=128
#   EXTRA_ARGS="--use_class_weight --early_stopping --patience 2"

PYTHON_BIN="${PYTHON_BIN:-python3}"
VENV_DIR="${VENV_DIR:-.venv}"
TRAIN_FILE="${TRAIN_FILE:-data/train_multiclass.csv}"
OUTPUT_DIR="${OUTPUT_DIR:-data/models/roberta-sentiment}"
MODEL_NAME="${MODEL_NAME:-hfl/chinese-roberta-wwm-ext}"
BATCH_SIZE="${BATCH_SIZE:-16}"
EPOCHS="${EPOCHS:-3}"
MAX_LENGTH="${MAX_LENGTH:-128}"
EXTRA_ARGS="${EXTRA_ARGS:-}"

echo "==> Creating virtual environment"
"${PYTHON_BIN}" -m venv "${VENV_DIR}"
source "${VENV_DIR}/bin/activate"

echo "==> Upgrading pip"
python -m pip install --upgrade pip

echo "==> Installing project dependencies"
pip install -r requirements.txt
pip install -r requirements-ml.txt

if [[ -n "${HF_ENDPOINT:-}" ]]; then
  echo "==> Using HF endpoint: ${HF_ENDPOINT}"
fi

echo "==> Validating training dataset"
python scripts/validate_training_data.py \
  --train_file "${TRAIN_FILE}" \
  --require_all_labels \
  --min_samples_per_label 500 \
  --output_json "${TRAIN_FILE%.csv}.validation.json"

echo "==> Starting baseline training"
python train_sentiment.py \
  --train_file "${TRAIN_FILE}" \
  --output_dir "${OUTPUT_DIR}" \
  --model_name "${MODEL_NAME}" \
  --batch_size "${BATCH_SIZE}" \
  --epochs "${EPOCHS}" \
  --max_length "${MAX_LENGTH}" \
  ${EXTRA_ARGS}

echo "==> Training finished"
echo "Model saved to: ${OUTPUT_DIR}"
