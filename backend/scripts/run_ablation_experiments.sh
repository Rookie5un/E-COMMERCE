#!/usr/bin/env bash
set -euo pipefail

# Batch ablation runner for sentiment fine-tuning experiments.
#
# Usage (run on server in backend/):
#   bash scripts/run_ablation_experiments.sh
#
# Optional environment overrides:
#   PYTHON_BIN=python3
#   TRAIN_FILE=data/train_balanced_full.csv
#   MODEL_NAME=hfl/chinese-roberta-wwm-ext
#   OUTPUT_ROOT=data/experiments
#   LOG_ROOT=logs/ablation
#   EXPERIMENT_NAME=ablation_v1
#   SEEDS="42 2024 3407"
#   EPOCHS=5
#   BATCH_SIZE=32
#   MAX_LENGTH=256
#   LEARNING_RATE=2e-5
#   TEST_SIZE=0.2
#   WARMUP_RATIO=0.1
#   WEIGHT_DECAY=0.01
#   PATIENCE=3
#
# Notes:
# - KFold is intentionally NOT used because current project implementation is placeholder.
# - "use_class_weight" is only effective together with focal loss in current train script.

PYTHON_BIN="${PYTHON_BIN:-python3}"
TRAIN_FILE="${TRAIN_FILE:-data/train_balanced_full.csv}"
MODEL_NAME="${MODEL_NAME:-hfl/chinese-roberta-wwm-ext}"
OUTPUT_ROOT="${OUTPUT_ROOT:-data/experiments}"
LOG_ROOT="${LOG_ROOT:-logs/ablation}"
EXPERIMENT_NAME="${EXPERIMENT_NAME:-ablation_$(date +%Y%m%d_%H%M%S)}"
SEEDS="${SEEDS:-42 2024 3407}"

EPOCHS="${EPOCHS:-5}"
BATCH_SIZE="${BATCH_SIZE:-32}"
MAX_LENGTH="${MAX_LENGTH:-256}"
LEARNING_RATE="${LEARNING_RATE:-2e-5}"
TEST_SIZE="${TEST_SIZE:-0.2}"
WARMUP_RATIO="${WARMUP_RATIO:-0.1}"
WEIGHT_DECAY="${WEIGHT_DECAY:-0.01}"
PATIENCE="${PATIENCE:-3}"

RUN_ROOT="${OUTPUT_ROOT}/${EXPERIMENT_NAME}"
RUN_LOG_ROOT="${LOG_ROOT}/${EXPERIMENT_NAME}"

mkdir -p "${RUN_ROOT}" "${RUN_LOG_ROOT}"

echo "========================================"
echo "Ablation experiment started"
echo "Experiment: ${EXPERIMENT_NAME}"
echo "Train file : ${TRAIN_FILE}"
echo "Model name : ${MODEL_NAME}"
echo "Run root   : ${RUN_ROOT}"
echo "Log root   : ${RUN_LOG_ROOT}"
echo "Seeds      : ${SEEDS}"
echo "========================================"

if [[ ! -f "${TRAIN_FILE}" ]]; then
  echo "ERROR: train file not found: ${TRAIN_FILE}" >&2
  exit 1
fi

common_args=(
  --train_file "${TRAIN_FILE}"
  --model_name "${MODEL_NAME}"
  --epochs "${EPOCHS}"
  --batch_size "${BATCH_SIZE}"
  --max_length "${MAX_LENGTH}"
  --learning_rate "${LEARNING_RATE}"
  --test_size "${TEST_SIZE}"
  --warmup_ratio "${WARMUP_RATIO}"
  --weight_decay "${WEIGHT_DECAY}"
)

run_one() {
  local group="$1"
  local seed="$2"
  shift 2

  local output_dir="${RUN_ROOT}/${group}/seed_${seed}"
  local log_file="${RUN_LOG_ROOT}/${group}_seed_${seed}.log"

  mkdir -p "${output_dir}" "$(dirname "${log_file}")"

  echo ""
  echo "[RUN] ${group} | seed=${seed}"
  echo "[OUT] ${output_dir}"
  echo "[LOG] ${log_file}"

  set -x
  "${PYTHON_BIN}" train_sentiment.py \
    "${common_args[@]}" \
    --output_dir "${output_dir}" \
    --seed "${seed}" \
    "$@" \
    > "${log_file}" 2>&1
  { set +x; } 2>/dev/null

  local summary_json="${output_dir}/training_summary.json"
  if [[ -f "${summary_json}" ]]; then
    echo "[OK ] Summary generated: ${summary_json}"
  else
    echo "[WARN] Summary missing: ${summary_json}" >&2
  fi
}

for seed in ${SEEDS}; do
  # A0: CE baseline
  run_one "A0_ce_baseline" "${seed}"

  # A1: baseline + FGM
  run_one "A1_ce_fgm" "${seed}" \
    --use_fgm

  # A2: baseline + FGM + warmup + early stopping
  run_one "A2_ce_fgm_es" "${seed}" \
    --use_fgm \
    --early_stopping \
    --patience "${PATIENCE}"

  # A3: A2 + focal + class weight
  run_one "A3_focal_fgm_es_cw" "${seed}" \
    --use_fgm \
    --early_stopping \
    --patience "${PATIENCE}" \
    --loss_type focal \
    --focal_gamma 2.0 \
    --use_class_weight

  # A4: A2 + label smoothing
  run_one "A4_ls_fgm_es" "${seed}" \
    --use_fgm \
    --early_stopping \
    --patience "${PATIENCE}" \
    --loss_type label_smoothing \
    --label_smoothing 0.1
done

echo ""
echo "========================================"
echo "Ablation experiment finished"
echo "Run root: ${RUN_ROOT}"
echo "Log root: ${RUN_LOG_ROOT}"
echo "Now run: ${PYTHON_BIN} scripts/collect_ablation_results.py --run_root ${RUN_ROOT}"
echo "========================================"
