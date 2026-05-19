#!/usr/bin/env bash
set -euo pipefail

# Minimal thesis experiment pipeline for running directly on a remote server.
#
# Default behavior is intentionally compact:
# 1. prepare / reuse .venv
# 2. validate dataset
# 3. run one reproducibility training (A2-style)
# 4. run a minimal core comparison
# 5. summarize ablation results and auto-pick the best group
# 6. run one final exportable model with seed=42
#
# Usage:
#   cd backend
#   bash scripts/run_thesis_minimal_server.sh
#
# Optional environment variables:
#   PYTHON_BIN=python3
#   VENV_DIR=.venv
#   SKIP_SETUP=0
#   PROFILE=minimal              # minimal | standard | full
#   GPU_IDS="0 1"               # space/comma separated GPU ids
#   PRIMARY_GPU_ID=0            # GPU used by repro/final single runs
#   TRAIN_FILE=data/train_balanced_full.csv
#   MODEL_NAME=hfl/chinese-roberta-wwm-ext
#   MAX_LENGTH=128
#   BATCH_SIZE=32
#   EPOCHS=5
#   LEARNING_RATE=2e-5
#   TEST_SIZE=0.2
#   WARMUP_RATIO=0.1
#   WEIGHT_DECAY=0.01
#   PATIENCE=3
#   EXPERIMENT_NAME=thesis_minimal_20260425
#   CORE_GROUPS="A0_ce_baseline A2_ce_fgm_es A3_focal_fgm_es_cw"
#   CORE_SEEDS="42 2024"
#   RUN_STABILITY=0
#   STABILITY_SEEDS="1234 5678 9999"
#   RUN_TESTS=0
#
# Output layout:
#   data/models/roberta-sentiment-thesis-repro
#   data/models/roberta-sentiment-thesis-final
#   data/experiments/<EXPERIMENT_NAME>
#   logs/thesis/<EXPERIMENT_NAME>

PYTHON_BIN="${PYTHON_BIN:-}"
VENV_DIR="${VENV_DIR:-.venv}"
SKIP_SETUP="${SKIP_SETUP:-0}"
PROFILE="${PROFILE:-minimal}"
GPU_IDS_RAW="${GPU_IDS:-0 1}"
PRIMARY_GPU_ID="${PRIMARY_GPU_ID:-}"

TRAIN_FILE="${TRAIN_FILE:-data/train_balanced_full.csv}"
MODEL_NAME="${MODEL_NAME:-hfl/chinese-roberta-wwm-ext}"
MAX_LENGTH="${MAX_LENGTH:-128}"
BATCH_SIZE="${BATCH_SIZE:-32}"
EPOCHS="${EPOCHS:-5}"
LEARNING_RATE="${LEARNING_RATE:-2e-5}"
TEST_SIZE="${TEST_SIZE:-0.2}"
WARMUP_RATIO="${WARMUP_RATIO:-0.1}"
WEIGHT_DECAY="${WEIGHT_DECAY:-0.01}"
PATIENCE="${PATIENCE:-3}"
VALIDATION_MAX_CONTENT_LENGTH="${VALIDATION_MAX_CONTENT_LENGTH:-1028}"

EXPERIMENT_NAME="${EXPERIMENT_NAME:-thesis_minimal_$(date +%Y%m%d_%H%M%S)}"
MODELS_ROOT="${MODELS_ROOT:-data/models}"
EXPERIMENTS_ROOT="${EXPERIMENTS_ROOT:-data/experiments}"
LOG_ROOT="${LOG_ROOT:-logs/thesis}"

REPRO_DIR="${REPRO_DIR:-${MODELS_ROOT}/roberta-sentiment-thesis-repro}"
FINAL_DIR="${FINAL_DIR:-${MODELS_ROOT}/roberta-sentiment-thesis-final}"
CORE_RUN_ROOT="${EXPERIMENTS_ROOT}/${EXPERIMENT_NAME}"
THIS_LOG_ROOT="${LOG_ROOT}/${EXPERIMENT_NAME}"

RUN_STABILITY="${RUN_STABILITY:-0}"
STABILITY_SEEDS="${STABILITY_SEEDS:-1234 5678 9999}"
FINAL_SEED="${FINAL_SEED:-42}"
RUN_TESTS="${RUN_TESTS:-0}"

CORE_GROUPS="${CORE_GROUPS:-}"
CORE_SEEDS="${CORE_SEEDS:-}"
declare -a GPU_ID_ARRAY=()
GPU_COUNT=1
LAST_ASYNC_PID=""

COMMON_ARGS=(
  --train_file "${TRAIN_FILE}"
  --model_name "${MODEL_NAME}"
  --max_length "${MAX_LENGTH}"
  --batch_size "${BATCH_SIZE}"
  --epochs "${EPOCHS}"
  --learning_rate "${LEARNING_RATE}"
  --test_size "${TEST_SIZE}"
  --warmup_ratio "${WARMUP_RATIO}"
  --weight_decay "${WEIGHT_DECAY}"
)

resolve_python_bin() {
  if [[ -n "${PYTHON_BIN}" ]]; then
    return
  fi

  if command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  elif command -v python >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python)"
  elif [[ -x "/root/miniconda3/bin/python" ]]; then
    PYTHON_BIN="/root/miniconda3/bin/python"
  else
    echo "ERROR: no usable python interpreter found; set PYTHON_BIN manually" >&2
    exit 1
  fi
}

init_gpu_config() {
  local normalized_gpu_ids
  normalized_gpu_ids="$(echo "${GPU_IDS_RAW}" | tr ',' ' ' | xargs)"

  if [[ -n "${normalized_gpu_ids}" ]]; then
    read -r -a GPU_ID_ARRAY <<< "${normalized_gpu_ids}"
  fi

  if [[ "${#GPU_ID_ARRAY[@]}" -eq 0 ]]; then
    GPU_ID_ARRAY=("0")
  fi

  GPU_COUNT="${#GPU_ID_ARRAY[@]}"

  if [[ -z "${PRIMARY_GPU_ID}" ]]; then
    PRIMARY_GPU_ID="${GPU_ID_ARRAY[0]}"
  fi
}

profile_defaults() {
  if [[ -n "${CORE_GROUPS}" && -n "${CORE_SEEDS}" ]]; then
    read -r -a CORE_GROUP_ARRAY <<< "${CORE_GROUPS}"
    read -r -a CORE_SEED_ARRAY <<< "${CORE_SEEDS}"
    return
  fi

  case "${PROFILE}" in
    minimal)
      CORE_GROUP_ARRAY=("A0_ce_baseline" "A2_ce_fgm_es" "A3_focal_fgm_es_cw")
      CORE_SEED_ARRAY=("42" "2024")
      ;;
    standard)
      CORE_GROUP_ARRAY=("A0_ce_baseline" "A1_ce_fgm" "A2_ce_fgm_es" "A3_focal_fgm_es_cw")
      CORE_SEED_ARRAY=("42" "2024" "3407")
      ;;
    full)
      CORE_GROUP_ARRAY=("A0_ce_baseline" "A1_ce_fgm" "A2_ce_fgm_es" "A3_focal_fgm_es_cw" "A4_ls_fgm_es")
      CORE_SEED_ARRAY=("42" "2024" "3407")
      ;;
    *)
      echo "ERROR: unsupported PROFILE=${PROFILE}" >&2
      exit 1
      ;;
  esac
}

group_extra_args() {
  local group="$1"
  GROUP_ARGS=()
  case "${group}" in
    A0_ce_baseline)
      ;;
    A1_ce_fgm)
      GROUP_ARGS+=(--use_fgm)
      ;;
    A2_ce_fgm_es)
      GROUP_ARGS+=(--use_fgm --early_stopping --patience "${PATIENCE}")
      ;;
    A3_focal_fgm_es_cw)
      GROUP_ARGS+=(--use_fgm --early_stopping --patience "${PATIENCE}" --loss_type focal --focal_gamma 2.0 --use_class_weight)
      ;;
    A4_ls_fgm_es)
      GROUP_ARGS+=(--use_fgm --early_stopping --patience "${PATIENCE}" --loss_type label_smoothing --label_smoothing 0.1)
      ;;
    *)
      echo "ERROR: unsupported group=${group}" >&2
      exit 1
      ;;
  esac
}

setup_env() {
  if [[ "${SKIP_SETUP}" == "1" ]]; then
    echo "==> Reusing existing virtualenv: ${VENV_DIR}"
  else
    if [[ ! -d "${VENV_DIR}" ]]; then
      echo "==> Creating virtualenv: ${VENV_DIR}"
      "${PYTHON_BIN}" -m venv "${VENV_DIR}"
    else
      echo "==> Virtualenv already exists: ${VENV_DIR}"
    fi
  fi

  # shellcheck disable=SC1090
  source "${VENV_DIR}/bin/activate"

  if [[ "${SKIP_SETUP}" != "1" ]]; then
    echo "==> Upgrading pip"
    python -m pip install --upgrade pip

    echo "==> Installing project dependencies"
    pip install -r requirements.txt
    pip install -r requirements-ml.txt
  fi

  echo "==> Python interpreter: ${PYTHON_BIN}"

  if command -v nvidia-smi >/dev/null 2>&1; then
    echo "==> GPU status"
    nvidia-smi || true
  else
    echo "==> nvidia-smi not found; training may run on CPU"
  fi

  echo "==> GPU config"
  echo "    visible GPUs for parallel jobs: ${GPU_ID_ARRAY[*]}"
  echo "    primary GPU for repro/final : ${PRIMARY_GPU_ID}"
}

validate_data() {
  echo "==> Validating dataset: ${TRAIN_FILE}"
  python scripts/validate_training_data.py \
    --train_file "${TRAIN_FILE}" \
    --require_all_labels \
    --min_samples_per_label 500 \
    --max_content_length "${VALIDATION_MAX_CONTENT_LENGTH}" \
    --output_json "${TRAIN_FILE%.csv}.validation.json"
}

run_train() {
  local label="$1"
  local output_dir="$2"
  local log_file="$3"
  local seed="$4"
  local gpu_id="${5:-}"
  shift 5

  mkdir -p "${output_dir}" "$(dirname "${log_file}")"

  echo ""
  echo "==> RUN ${label}"
  echo "    output: ${output_dir}"
  echo "    log   : ${log_file}"
  echo "    seed  : ${seed}"
  if [[ -n "${gpu_id}" ]]; then
    echo "    gpu   : ${gpu_id}"
  fi

  if [[ -n "${gpu_id}" ]]; then
    CUDA_VISIBLE_DEVICES="${gpu_id}" \
      python train_sentiment.py \
        "${COMMON_ARGS[@]}" \
        --output_dir "${output_dir}" \
        --seed "${seed}" \
        "$@" \
        > "${log_file}" 2>&1
  else
    python train_sentiment.py \
      "${COMMON_ARGS[@]}" \
      --output_dir "${output_dir}" \
      --seed "${seed}" \
      "$@" \
      > "${log_file}" 2>&1
  fi

  if [[ ! -f "${output_dir}/training_summary.json" ]]; then
    echo "ERROR: training_summary.json not generated for ${label}" >&2
    exit 1
  fi
}

run_train_async() {
  local label="$1"
  local output_dir="$2"
  local log_file="$3"
  local seed="$4"
  local gpu_id="$5"
  shift 5

  mkdir -p "${output_dir}" "$(dirname "${log_file}")"

  (
    set -euo pipefail
    echo "" >&2
    echo "==> RUN ${label}" >&2
    echo "    output: ${output_dir}" >&2
    echo "    log   : ${log_file}" >&2
    echo "    seed  : ${seed}" >&2
    echo "    gpu   : ${gpu_id}" >&2

    CUDA_VISIBLE_DEVICES="${gpu_id}" \
      python train_sentiment.py \
        "${COMMON_ARGS[@]}" \
        --output_dir "${output_dir}" \
        --seed "${seed}" \
        "$@" \
        > "${log_file}" 2>&1

    if [[ ! -f "${output_dir}/training_summary.json" ]]; then
      echo "ERROR: training_summary.json not generated for ${label}" >&2
      exit 1
    fi
  ) &

  LAST_ASYNC_PID="$!"
}

wait_batch() {
  local -n pid_array_ref=$1
  local -n label_array_ref=$2
  local index

  for index in "${!pid_array_ref[@]}"; do
    local pid="${pid_array_ref[$index]}"
    local label="${label_array_ref[$index]}"
    if ! wait "${pid}"; then
      echo "ERROR: parallel job failed: ${label}" >&2
      exit 1
    fi
  done
}

run_parallel_tasks() {
  local -n task_group_array_ref=$1
  local -n task_seed_array_ref=$2

  local -a batch_pids=()
  local -a batch_labels=()
  local gpu_index=0
  local batch_size=0
  local task_index

  for task_index in "${!task_group_array_ref[@]}"; do
    local group="${task_group_array_ref[$task_index]}"
    local seed="${task_seed_array_ref[$task_index]}"
    local gpu_id="${GPU_ID_ARRAY[$gpu_index]}"
    local label="${group}_seed_${seed}"

    group_extra_args "${group}"
    run_train_async \
      "${group}" \
      "${CORE_RUN_ROOT}/${group}/seed_${seed}" \
      "${THIS_LOG_ROOT}/${group}_seed_${seed}.log" \
      "${seed}" \
      "${gpu_id}" \
      "${GROUP_ARGS[@]}"

    batch_pids+=("${LAST_ASYNC_PID}")
    batch_labels+=("${label}")
    batch_size=$((batch_size + 1))
    gpu_index=$((gpu_index + 1))

    if (( gpu_index >= GPU_COUNT )); then
      gpu_index=0
    fi

    if (( batch_size >= GPU_COUNT )); then
      wait_batch batch_pids batch_labels
      batch_pids=()
      batch_labels=()
      batch_size=0
      gpu_index=0
    fi
  done

  if (( batch_size > 0 )); then
    wait_batch batch_pids batch_labels
  fi
}

run_parallel_stability_tasks() {
  local -n stability_seed_array_ref=$1
  local stability_root="$2"

  local -a batch_pids=()
  local -a batch_labels=()
  local gpu_index=0
  local batch_size=0
  local seed

  group_extra_args "${BEST_GROUP}"

  for seed in "${stability_seed_array_ref[@]}"; do
    local gpu_id="${GPU_ID_ARRAY[$gpu_index]}"
    local label="stability_${BEST_GROUP}_seed_${seed}"
    run_train_async \
      "stability_${BEST_GROUP}" \
      "${stability_root}/seed_${seed}" \
      "${THIS_LOG_ROOT}/stability_${BEST_GROUP}_seed_${seed}.log" \
      "${seed}" \
      "${gpu_id}" \
      "${GROUP_ARGS[@]}"

    batch_pids+=("${LAST_ASYNC_PID}")
    batch_labels+=("${label}")
    batch_size=$((batch_size + 1))
    gpu_index=$((gpu_index + 1))

    if (( gpu_index >= GPU_COUNT )); then
      gpu_index=0
    fi

    if (( batch_size >= GPU_COUNT )); then
      wait_batch batch_pids batch_labels
      batch_pids=()
      batch_labels=()
      batch_size=0
      gpu_index=0
    fi
  done

  if (( batch_size > 0 )); then
    wait_batch batch_pids batch_labels
  fi
}

run_repro() {
  local repro_log="${THIS_LOG_ROOT}/repro_seed_${FINAL_SEED}.log"
  run_train \
    "repro_A2_style" \
    "${REPRO_DIR}" \
    "${repro_log}" \
    "${FINAL_SEED}" \
    "${PRIMARY_GPU_ID}" \
    --use_fgm \
    --early_stopping \
    --patience "${PATIENCE}"
}

run_core() {
  echo ""
  echo "==> Running core comparison"
  echo "    groups: ${CORE_GROUP_ARRAY[*]}"
  echo "    seeds : ${CORE_SEED_ARRAY[*]}"

  local -a TASK_GROUP_ARRAY=()
  local -a TASK_SEED_ARRAY=()
  local group
  local seed

  for group in "${CORE_GROUP_ARRAY[@]}"; do
    for seed in "${CORE_SEED_ARRAY[@]}"; do
      TASK_GROUP_ARRAY+=("${group}")
      TASK_SEED_ARRAY+=("${seed}")
    done
  done

  run_parallel_tasks TASK_GROUP_ARRAY TASK_SEED_ARRAY
}

summarize_core() {
  echo ""
  echo "==> Collecting ablation summary"
  python scripts/collect_ablation_results.py --run_root "${CORE_RUN_ROOT}"
}

pick_best_group() {
  BEST_GROUP="$(
    python scripts/select_best_ablation.py \
      --summary_csv "${CORE_RUN_ROOT}/summary/ablation_group_summary.csv"
  )"
  export BEST_GROUP
  echo "==> Best group selected: ${BEST_GROUP}"
}

run_stability() {
  if [[ "${RUN_STABILITY}" != "1" ]]; then
    echo "==> Stability runs skipped (RUN_STABILITY=${RUN_STABILITY})"
    return
  fi

  echo ""
  echo "==> Running stability checks for ${BEST_GROUP}"

  read -r -a STABILITY_SEED_ARRAY <<< "${STABILITY_SEEDS}"
  local stability_root="${EXPERIMENTS_ROOT}/${EXPERIMENT_NAME}_stability/${BEST_GROUP}"
  run_parallel_stability_tasks STABILITY_SEED_ARRAY "${stability_root}"
}

run_final() {
  echo ""
  echo "==> Exporting final thesis model from best group: ${BEST_GROUP}"
  group_extra_args "${BEST_GROUP}"

  run_train \
    "final_${BEST_GROUP}" \
    "${FINAL_DIR}" \
    "${THIS_LOG_ROOT}/final_${BEST_GROUP}_seed_${FINAL_SEED}.log" \
    "${FINAL_SEED}" \
    "${PRIMARY_GPU_ID}" \
    "${GROUP_ARGS[@]}"
}

run_tests() {
  if [[ "${RUN_TESTS}" != "1" ]]; then
    echo "==> Backend tests skipped (RUN_TESTS=${RUN_TESTS})"
    return
  fi

  echo ""
  echo "==> Running backend tests"
  python -m unittest discover -s tests -v | tee "${THIS_LOG_ROOT}/backend_unittest.log"
}

print_summary() {
  echo ""
  echo "========================================"
  echo "Thesis minimal experiment pipeline finished"
  echo "Profile           : ${PROFILE}"
  echo "Dataset           : ${TRAIN_FILE}"
  echo "Experiment name   : ${EXPERIMENT_NAME}"
  echo "Repro model       : ${REPRO_DIR}"
  echo "Core run root     : ${CORE_RUN_ROOT}"
  echo "Core summary csv  : ${CORE_RUN_ROOT}/summary/ablation_group_summary.csv"
  echo "Best group        : ${BEST_GROUP}"
  echo "Final model       : ${FINAL_DIR}"
  if [[ "${RUN_STABILITY}" == "1" ]]; then
    echo "Stability root     : ${EXPERIMENTS_ROOT}/${EXPERIMENT_NAME}_stability/${BEST_GROUP}"
  fi
  echo "Logs              : ${THIS_LOG_ROOT}"
  echo "========================================"
}

main() {
  if [[ ! -f "${TRAIN_FILE}" ]]; then
    echo "ERROR: train file not found: ${TRAIN_FILE}" >&2
    exit 1
  fi

  mkdir -p "${MODELS_ROOT}" "${EXPERIMENTS_ROOT}" "${THIS_LOG_ROOT}"
  init_gpu_config
  resolve_python_bin
  profile_defaults
  setup_env
  validate_data
  run_repro
  run_core
  summarize_core
  pick_best_group
  run_stability
  run_final
  run_tests
  print_summary
}

main "$@"
