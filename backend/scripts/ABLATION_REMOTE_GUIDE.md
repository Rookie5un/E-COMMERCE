# 使用 run_ablation_remote.sh 进行对比实验指南

## 基本用法

`run_ablation_remote.sh` 已经支持完整的对比实验功能，你只需要通过环境变量配置不同的实验即可。

## 实验1：稳定性测试（多种子对比）

验证模型训练的稳定性，使用多个随机种子：

```bash
cd backend

# 本地运行
EXPERIMENT_NAME=stability_test \
SEEDS="42 2024 3407 1234 5678 9999 2025 2026" \
bash scripts/run_ablation_experiments.sh

# 远程运行
SERVER_USER=root \
SERVER_HOST=YOUR_SERVER_IP \
EXPERIMENT_NAME=stability_test \
SEEDS="42 2024 3407 1234 5678 9999 2025 2026" \
bash scripts/run_ablation_remote.sh
```

**结果**：8次训练，每次使用不同种子，对比性能稳定性

---

## 实验2：消融实验（默认配置）

对比不同优化策略的效果，这是脚本的默认行为：

```bash
cd backend

# 本地运行（使用默认的5组实验）
EXPERIMENT_NAME=ablation_v1 \
bash scripts/run_ablation_experiments.sh

# 远程运行
SERVER_USER=root \
SERVER_HOST=YOUR_SERVER_IP \
EXPERIMENT_NAME=ablation_v1 \
bash scripts/run_ablation_remote.sh
```

**默认实验组**：
- A0: CE baseline
- A1: CE + FGM
- A2: CE + FGM + 早停
- A3: Focal + FGM + 早停 + 类别权重
- A4: Label Smoothing + FGM + 早停

**结果**：5组 × 3种子 = 15次训练

---

## 实验3：超参数对比

对比不同超参数配置的效果：

### 3.1 学习率对比

```bash
# 学习率 1e-5
EXPERIMENT_NAME=lr_1e5 \
LEARNING_RATE=1e-5 \
bash scripts/run_ablation_remote.sh

# 学习率 2e-5（默认）
EXPERIMENT_NAME=lr_2e5 \
LEARNING_RATE=2e-5 \
bash scripts/run_ablation_remote.sh

# 学习率 3e-5
EXPERIMENT_NAME=lr_3e5 \
LEARNING_RATE=3e-5 \
bash scripts/run_ablation_remote.sh
```

### 3.2 批次大小对比

```bash
# 批次大小 16
EXPERIMENT_NAME=bs_16 \
BATCH_SIZE=16 \
bash scripts/run_ablation_remote.sh

# 批次大小 32（默认）
EXPERIMENT_NAME=bs_32 \
BATCH_SIZE=32 \
bash scripts/run_ablation_remote.sh

# 批次大小 64
EXPERIMENT_NAME=bs_64 \
BATCH_SIZE=64 \
bash scripts/run_ablation_remote.sh
```

### 3.3 序列长度对比

```bash
# 序列长度 128
EXPERIMENT_NAME=ml_128 \
MAX_LENGTH=128 \
bash scripts/run_ablation_remote.sh

# 序列长度 256（默认）
EXPERIMENT_NAME=ml_256 \
MAX_LENGTH=256 \
bash scripts/run_ablation_remote.sh

# 序列长度 512
EXPERIMENT_NAME=ml_512 \
MAX_LENGTH=512 \
bash scripts/run_ablation_remote.sh
```

---

## 实验4：训练轮数对比

```bash
# 3轮训练
EXPERIMENT_NAME=epochs_3 \
EPOCHS=3 \
bash scripts/run_ablation_remote.sh

# 5轮训练（默认）
EXPERIMENT_NAME=epochs_5 \
EPOCHS=5 \
bash scripts/run_ablation_remote.sh

# 10轮训练
EXPERIMENT_NAME=epochs_10 \
EPOCHS=10 \
bash scripts/run_ablation_remote.sh
```

---

## 实验5：组合超参数对比

对比多个超参数的最优组合：

```bash
# 配置1：小批次 + 低学习率
EXPERIMENT_NAME=config_1 \
BATCH_SIZE=16 \
LEARNING_RATE=1e-5 \
MAX_LENGTH=256 \
bash scripts/run_ablation_remote.sh

# 配置2：中批次 + 中学习率（默认）
EXPERIMENT_NAME=config_2 \
BATCH_SIZE=32 \
LEARNING_RATE=2e-5 \
MAX_LENGTH=256 \
bash scripts/run_ablation_remote.sh

# 配置3：大批次 + 高学习率
EXPERIMENT_NAME=config_3 \
BATCH_SIZE=64 \
LEARNING_RATE=3e-5 \
MAX_LENGTH=256 \
bash scripts/run_ablation_remote.sh
```

---

## 收集和对比结果

### 单个实验结果

```bash
cd backend

# 收集单个实验的结果
python3 scripts/collect_ablation_results.py \
  --run_root data/experiments/ablation_v1

# 查看结果
cat data/experiments/ablation_v1/summary/ablation_group_summary.md
```

### 对比多个实验

如果你运行了多个实验（如不同学习率），可以手动对比：

```bash
# 查看所有实验的最优F1
for exp in lr_1e5 lr_2e5 lr_3e5; do
  echo "=== ${exp} ==="
  cat data/experiments/${exp}/summary/ablation_group_summary.csv | \
    tail -n +2 | sort -t',' -k5 -rn | head -1
done
```

### 合并多个实验结果

创建一个简单的对比脚本：

```bash
cat > compare_experiments.sh <<'EOF'
#!/bin/bash
echo "实验名称,组别,准确率均值,F1均值"
for exp_dir in data/experiments/*/; do
  exp_name=$(basename "$exp_dir")
  if [[ -f "${exp_dir}summary/ablation_group_summary.csv" ]]; then
    tail -n +2 "${exp_dir}summary/ablation_group_summary.csv" | \
    while IFS=, read -r group n_runs acc_mean acc_std f1_mean f1_std; do
      echo "${exp_name},${group},${acc_mean},${f1_mean}"
    done
  fi
done | column -t -s','
EOF

chmod +x compare_experiments.sh
./compare_experiments.sh
```

---

## 推荐的实验流程

### 阶段1：验证稳定性（1-2天）

```bash
# 使用8个种子验证当前配置的稳定性
SERVER_USER=root \
SERVER_HOST=YOUR_SERVER_IP \
EXPERIMENT_NAME=stability_baseline \
SEEDS="42 2024 3407 1234 5678 9999 2025 2026" \
bash scripts/run_ablation_remote.sh
```

收集结果后，检查标准差：
- 如果 std < 0.5%，说明训练稳定
- 如果 std > 1%，需要调查原因

### 阶段2：消融实验（2-3天）

```bash
# 运行默认的消融实验
SERVER_USER=root \
SERVER_HOST=YOUR_SERVER_IP \
EXPERIMENT_NAME=ablation_full \
SEEDS="42 2024 3407" \
bash scripts/run_ablation_remote.sh
```

找出最优的优化策略组合（如 A2 或 A3）

### 阶段3：超参数调优（3-5天）

基于阶段2的最优策略，测试不同超参数：

```bash
# 测试3个学习率
for lr in 1e-5 2e-5 3e-5; do
  SERVER_USER=root \
  SERVER_HOST=YOUR_SERVER_IP \
  EXPERIMENT_NAME=tune_lr_${lr} \
  LEARNING_RATE=${lr} \
  bash scripts/run_ablation_remote.sh
done

# 测试3个批次大小
for bs in 16 32 64; do
  SERVER_USER=root \
  SERVER_HOST=YOUR_SERVER_IP \
  EXPERIMENT_NAME=tune_bs_${bs} \
  BATCH_SIZE=${bs} \
  bash scripts/run_ablation_remote.sh
done
```

---

## 环境变量完整列表

```bash
# 服务器配置
SERVER_USER=root              # SSH用户名
SERVER_HOST=YOUR_SERVER_IP    # 服务器IP
SERVER_PORT=22                # SSH端口
REMOTE_PROJECT_DIR=~/E-commerce  # 远程项目目录

# 实验配置
EXPERIMENT_NAME=ablation_v1   # 实验名称
PYTHON_BIN=python3            # Python解释器
TRAIN_FILE=data/train_balanced_full.csv  # 训练数据
MODEL_NAME=hfl/chinese-roberta-wwm-ext   # 预训练模型

# 训练超参数
SEEDS="42 2024 3407"          # 随机种子（空格分隔）
EPOCHS=5                      # 训练轮数
BATCH_SIZE=32                 # 批次大小
MAX_LENGTH=256                # 最大序列长度
LEARNING_RATE=2e-5            # 学习率
TEST_SIZE=0.2                 # 验证集比例
WARMUP_RATIO=0.1              # 预热比例
WEIGHT_DECAY=0.01             # 权重衰减
PATIENCE=3                    # 早停耐心值

# 输出配置
OUTPUT_ROOT=data/experiments  # 实验输出根目录
LOG_ROOT=logs/ablation        # 日志根目录
```

---

## 常见问题

**Q: 如何只运行部分实验组？**

A: 你需要修改 `run_ablation_experiments.sh` 脚本，注释掉不需要的组。或者运行完整实验后，只分析你关心的组。

**Q: 如何在后台运行远程实验？**

```bash
# 使用nohup
nohup bash scripts/run_ablation_remote.sh > remote_experiment.log 2>&1 &

# 或者在远程服务器上使用tmux
ssh user@server
tmux new -s experiment
cd ~/E-commerce/backend
bash scripts/run_ablation_experiments.sh
# Ctrl+B, D 分离会话
```

**Q: 如何检查远程实验进度？**

```bash
# SSH到服务器
ssh user@server

# 查看日志
tail -f ~/E-commerce/logs/ablation/*/A0_ce_baseline_seed_42.log

# 统计已完成的实验
find ~/E-commerce/data/experiments/ablation_* -name "training_summary.json" | wc -l
```

**Q: 如何下载远程实验结果？**

```bash
# 下载整个实验目录
rsync -avz user@server:~/E-commerce/data/experiments/ablation_v1/ \
  ./data/experiments/ablation_v1/

# 只下载summary
rsync -avz user@server:~/E-commerce/data/experiments/ablation_v1/summary/ \
  ./data/experiments/ablation_v1/summary/
```

---

## 总结

使用 `run_ablation_remote.sh` 进行对比实验的优势：

✅ **无需修改代码** - 通过环境变量控制所有配置
✅ **支持远程执行** - 自动同步代码并在服务器上运行
✅ **灵活组合** - 可以对比任意超参数组合
✅ **结果标准化** - 使用统一的结果收集脚本

你只需要：
1. 设置服务器配置（SERVER_HOST等）
2. 选择要对比的参数（LEARNING_RATE、BATCH_SIZE等）
3. 运行脚本
4. 收集和分析结果

就这么简单！
