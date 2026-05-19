# 毕设实验实施方案（远程服务器版）

## Summary
- 这次不改代码接口，重点是把“论文里该有的实验”做成一套可复现、可落表、可落图、可答辩的实验链路。公共 API / 类型变更：无。
- 主实验只围绕项目当前真实主线展开：`train_balanced_full.csv` 上的中文 RoBERTa 三分类情感分析，不把仓库里尚未正式落地的方向写成已完成成果。
- 论文中的实验证据分两类：
  - 现有已核实证据：直接用仓库已有日志，支撑“历史基线 vs 当前部署模型”的训练数据平衡化收益。
  - 远程补做证据：在服务器上完成核心对比实验、稳定性实验和代表性运行，用于更新第五章和第七章。
- 主评价指标固定为 `Macro-F1`，次指标为 `Accuracy`，类别级指标固定展示 `Precision / Recall / F1`。配置优劣判断顺序固定为：`macro_f1_mean` > `accuracy_mean` > `macro_f1_std`（越小越稳）。

## 实验集设计
### 1. 已有结果复用实验
- 直接使用现有两组日志做“训练数据版本对比”：
  - 历史基线：`backend/logs/train_2026-04-17-1318.log`
    - 数据集：`train_multiclass_plus_public.csv`
    - 结果：`Accuracy=0.9295`，`Macro-F1=0.8996`
  - 当前部署模型：`backend/data/models/roberta-sentiment-balanced/training.log`
    - 数据集：`train_balanced_full.csv`
    - 结果：`Accuracy=0.9370`，`Macro-F1=0.9352`
- 论文用途：
  - 第五章写“中性样本扩充与平衡化训练收益”
  - 第七章写“已有结果分析”
- 这组结果保留，不因后续远程补实验而删除；后续新实验只作为补强，不覆盖其“项目演进证据”角色。

### 2. 远程复现实验
- 目标：在远程服务器上复现当前部署模型的同配置结果，证明实验环境可用。
- 固定配置：
  - 数据集：`data/train_balanced_full.csv`
  - 预训练模型：`hfl/chinese-roberta-wwm-ext`
  - `max_length=128`
  - `batch_size=32`
  - `epochs=5`
  - `learning_rate=2e-5`
  - `warmup_ratio=0.1`
  - `weight_decay=0.01`
  - `test_size=0.2`
  - `seed=42`
  - `use_fgm=True`
  - `early_stopping=True`
  - `loss_type=ce`
- 输出目录固定为：`data/models/roberta-sentiment-thesis-repro`
- 论文用途：
  - 验证服务器环境和当前项目配置一致
  - 为后续消融实验提供统一参照组

### 3. 核心对比实验
- 主数据集固定：`data/train_balanced_full.csv`
- 主实验组固定做 4 组，`A4` 作为可选补强：
  - `A0_ce_baseline`：CE baseline
  - `A1_ce_fgm`：CE + FGM
  - `A2_ce_fgm_es`：CE + FGM + Early Stopping
  - `A3_focal_fgm_es_cw`：Focal Loss + FGM + Early Stopping + Class Weight
  - `A4_ls_fgm_es`：Label Smoothing + FGM + Early Stopping（时间允许再做）
- 统一控制变量：
  - `max_length=128`
  - `batch_size=32`
  - `epochs=5`
  - `learning_rate=2e-5`
  - `warmup_ratio=0.1`
  - `weight_decay=0.01`
  - `test_size=0.2`
- 随机种子固定：
  - 必做：`42 2024 3407`
  - 如果时间紧，只保留这 3 个种子，不再扩大
- 运行产物固定输出到：
  - `data/experiments/thesis_core`
  - `logs/ablation/thesis_core`
- 论文用途：
  - 第五章：实验设计与配置说明
  - 第七章：核心对比结果表、均值和标准差分析

### 4. 稳定性实验
- 目标：只对核心对比实验中表现最好的组做额外稳定性验证，不对所有组扩大战线。
- 最佳组选择规则固定：
  - 先看 `macro_f1_mean`
  - 相同则看 `accuracy_mean`
  - 再相同则选 `macro_f1_std` 更低的组
- 稳定性实验种子固定：
  - `1234 5678 9999`
- 运行目录固定：
  - `data/experiments/thesis_stability`
- 论文用途：
  - 第七章补一张“最佳组稳定性表”
  - 如果标准差较小，可支撑“模型训练稳定”

### 5. 代表性运行实验
- 目标：为论文生成一组“类别级指标表”和“可部署模型产物”。
- 配置固定：
  - 使用核心对比实验中的最佳组配置
  - 使用 `seed=42`
- 输出目录固定：
  - `data/models/roberta-sentiment-thesis-final`
- 这组运行的作用不是做均值比较，而是提供：
  - 最终 `training_summary.json`
  - 最终 `training_args.txt`
  - 最终 `dataset_summary.json`
  - 最终日志中的分类报告
- 论文用途：
  - 第七章“类别级指标表”
  - 附录“最终模型训练配置”

## 执行步骤
### 1. 远程环境准备
- 服务器预设条件：
  - 至少 1 张 NVIDIA GPU
  - Python 3.10-3.12
  - 可联网下载 Hugging Face 模型，或已配置镜像
  - 可用磁盘至少 50GB
- 远程首次准备命令：
```bash
ssh <SERVER_USER>@<SERVER_HOST>
cd ~/E-commerce/backend
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install -r requirements-ml.txt
python scripts/validate_training_data.py \
  --train_file data/train_balanced_full.csv \
  --require_all_labels \
  --min_samples_per_label 500 \
  --output_json data/train_balanced_full.validation.json
nvidia-smi
```
- 如果下载模型受限，固定处理顺序：
  - 优先设置 `HF_ENDPOINT`
  - 再考虑预先手动下载模型缓存
  - 不在论文中写“已完成实验”，直到模型真正跑通

### 2. 远程复现实验
```bash
cd ~/E-commerce/backend
source .venv/bin/activate
python train_sentiment.py \
  --train_file data/train_balanced_full.csv \
  --output_dir data/models/roberta-sentiment-thesis-repro \
  --model_name hfl/chinese-roberta-wwm-ext \
  --max_length 128 \
  --batch_size 32 \
  --epochs 5 \
  --learning_rate 2e-5 \
  --warmup_ratio 0.1 \
  --weight_decay 0.01 \
  --test_size 0.2 \
  --seed 42 \
  --use_fgm \
  --early_stopping \
  --patience 3
```
- 验收标准：
  - 目录下生成 `training_summary.json`
  - 日志中出现完整分类报告
  - 指标与已有 `0.9370 / 0.9352` 不必完全一致，但如果偏差超过 `±1.0%`，先排查环境差异，再继续消融

### 3. 核心对比实验
- 推荐从本地直接触发远程同步脚本：
```bash
cd backend
SERVER_USER=<SERVER_USER> \
SERVER_HOST=<SERVER_HOST> \
SERVER_PORT=22 \
REMOTE_PROJECT_DIR=~/E-commerce \
EXPERIMENT_NAME=thesis_core \
TRAIN_FILE=data/train_balanced_full.csv \
MODEL_NAME=hfl/chinese-roberta-wwm-ext \
SEEDS="42 2024 3407" \
EPOCHS=5 \
BATCH_SIZE=32 \
MAX_LENGTH=128 \
LEARNING_RATE=2e-5 \
TEST_SIZE=0.2 \
WARMUP_RATIO=0.1 \
WEIGHT_DECAY=0.01 \
PATIENCE=3 \
bash scripts/run_ablation_remote.sh
```
- 远程汇总：
```bash
ssh <SERVER_USER>@<SERVER_HOST>
cd ~/E-commerce/backend
source .venv/bin/activate
python3 scripts/collect_ablation_results.py --run_root data/experiments/thesis_core
```
- 预期产物：
  - `ablation_raw_runs.csv`
  - `ablation_group_summary.csv`
  - `ablation_group_summary.md`
  - `ablation_accuracy.png`
  - `ablation_macro_f1.png`

### 4. 稳定性实验
- 先从 `thesis_core/summary/ablation_group_summary.csv` 选出最佳组。
- 然后只对该组做额外种子复验；由于现有脚本会默认跑所有组，稳定性实验建议手动执行单组训练，避免浪费时间：
```bash
cd ~/E-commerce/backend
source .venv/bin/activate

for SEED in 1234 5678 9999; do
  python train_sentiment.py \
    --train_file data/train_balanced_full.csv \
    --output_dir data/experiments/thesis_stability/<BEST_GROUP>/seed_${SEED} \
    --model_name hfl/chinese-roberta-wwm-ext \
    --max_length 128 \
    --batch_size 32 \
    --epochs 5 \
    --learning_rate 2e-5 \
    --warmup_ratio 0.1 \
    --weight_decay 0.01 \
    --test_size 0.2 \
    --seed ${SEED} \
    <BEST_GROUP_EXTRA_ARGS> \
    > logs/ablation/thesis_stability_<BEST_GROUP>_seed_${SEED}.log 2>&1
done
```
- `<BEST_GROUP_EXTRA_ARGS>` 固定替换规则：
  - 如果最佳组是 `A0`：留空
  - `A1`：`--use_fgm`
  - `A2`：`--use_fgm --early_stopping --patience 3`
  - `A3`：`--use_fgm --early_stopping --patience 3 --loss_type focal --focal_gamma 2.0 --use_class_weight`
  - `A4`：`--use_fgm --early_stopping --patience 3 --loss_type label_smoothing --label_smoothing 0.1`

### 5. 代表性运行实验
- 使用最佳组配置，固定 `seed=42` 再跑一次正式模型：
```bash
cd ~/E-commerce/backend
source .venv/bin/activate
python train_sentiment.py \
  --train_file data/train_balanced_full.csv \
  --output_dir data/models/roberta-sentiment-thesis-final \
  --model_name hfl/chinese-roberta-wwm-ext \
  --max_length 128 \
  --batch_size 32 \
  --epochs 5 \
  --learning_rate 2e-5 \
  --warmup_ratio 0.1 \
  --weight_decay 0.01 \
  --test_size 0.2 \
  --seed 42 \
  <BEST_GROUP_EXTRA_ARGS>
```
- 这次运行后，固定从日志中提取类别级 `precision / recall / f1-score`，写入论文最终类别级结果表。

### 6. 平台验证实验
- 这是论文“工程验证”部分，不与模型消融混写。
- 远程环境依赖装好后，补跑后端单测：
```bash
cd ~/E-commerce/backend
source .venv/bin/activate
python -m unittest discover -s tests -v
```
- 论文写法固定：
  - 如果跑通：写“已在远程实验环境执行”
  - 如果仍有依赖或环境限制：写“已提供测试代码并在当前环境完成静态核对，未全部执行的原因是……”
- 不允许把未执行测试写成“已通过”。

## Thesis Outputs
### 必放表格
- 数据集统计表：
  - `train_multiclass.csv`
  - `train_multiclass_plus_public.csv`
  - `train_balanced_full.csv`
- 实验环境表：
  - 服务器型号、GPU、CUDA、Python、Torch、Transformers
- 核心对比配置表：
  - A0-A4 的差异
- 核心对比结果表：
  - `accuracy_mean`
  - `accuracy_std`
  - `macro_f1_mean`
  - `macro_f1_std`
- 类别级结果表：
  - 取 `roberta-sentiment-thesis-final` 的分类报告
- 稳定性结果表：
  - 最佳组的 3 个额外种子结果

### 必放图片
- 训练数据版本对比图：
  - 用已有两组日志结果手工制图或 Excel 作图
- 核心对比 Accuracy 图：
  - `ablation_accuracy.png`
- 核心对比 Macro-F1 图：
  - `ablation_macro_f1.png`
- 稳定性图：
  - 最佳组不同种子的柱状图或箱线图
- 系统页面截图与 PDF 报告截图：
  - 单独放在系统实现章节，不与实验图混用

### 固定写法
- 第五章：
  - 写训练数据构建、脚本结构、参数设计、已有平衡化收益证据
- 第七章：
  - 先写平台验证
  - 再写已有历史结果
  - 再写远程核心对比实验
  - 最后写稳定性与边界说明
- 任何新数字只有在以下文件都存在时才允许写入正文：
  - 运行日志
  - `training_summary.json` 或 `ablation_group_summary.csv`

## Acceptance Criteria
- 远程复现实验目录、核心对比实验目录、稳定性目录和最终模型目录全部生成。
- 每次正式训练都有 `training_summary.json`，每个核心实验组至少有 3 个种子。
- `collect_ablation_results.py` 成功输出 `csv + md + png`。
- 论文最终只引用真实生成的实验结果；未跑出的实验只写成“实验设计”或“后续工作”。
- 系统验证和模型实验分章叙述，不把自动化测试结果和模型对比结果混在同一张表里。

## Assumptions
- 默认服务器有 GPU；若只有 CPU，缩减为：
  - 只做远程复现实验
  - 只做 `A0 / A2 / A3` 单种子实验
  - 不做稳定性实验
- 默认主实验使用 `MAX_LENGTH=128`，因为这与项目当前已核实模型配置一致，且更利于和现有日志对齐。
- 默认 `A4` 为可选项；如果时间不够，论文只保留 `A0-A3` 四组即可。
- 默认最终代表性类别级结果取最佳组的 `seed=42` 运行，不再额外挑选“最好看的种子”。

cd /root/autodl-tmp/E-commerce/backend
SKIP_SETUP=1 bash scripts/run_thesis_minimal_server.sh

cd /root/autodl-tmp/E-commerce/backend
GPU_IDS="0 1" PRIMARY_GPU_ID=0 PROFILE=standard RUN_STABILITY=1 bash scripts/run_thesis_minimal_server.sh

data/experiments/<EXPERIMENT_NAME>/summary/ablation_group_summary.csv
data/experiments/<EXPERIMENT_NAME>/summary/ablation_accuracy.png
data/experiments/<EXPERIMENT_NAME>/summary/ablation_macro_f1.png
data/models/roberta-sentiment-thesis-final/training_summary.json
logs/thesis/<EXPERIMENT_NAME>/ 里的最终日志