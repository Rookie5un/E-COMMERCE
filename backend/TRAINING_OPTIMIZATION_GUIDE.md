# 模型训练优化指南

本文档介绍了电商评论情感分析模型的训练优化功能。

## 新增优化功能

### 高优先级优化（已实施）

#### 1. 增加 max_length 到 256
- **目标**: 避免长评论被截断，提升长文本情感分析准确率
- **使用**: `--max_length 256`（默认值已更新）

#### 2. Focal Loss 处理类别不平衡
- **目标**: 改善少数类（中性评论）的识别效果
- **使用**: `--loss_type focal --focal_gamma 2.0`
- **参数说明**:
  - `focal_gamma`: 聚焦参数，推荐值 2.0
  - 值越大，模型越关注难分类样本

#### 3. 标签平滑（Label Smoothing）
- **目标**: 防止模型过拟合，提升泛化能力
- **使用**: `--loss_type label_smoothing --label_smoothing 0.1`
- **参数说明**:
  - `label_smoothing`: 平滑系数，推荐值 0.1

#### 4. 高级数据增强
- **目标**: 通过同义词替换、随机插入/交换/删除提升模型泛化能力
- **功能**: 自动应用，训练时 30% 概率触发
- **策略**:
  - 同义词替换：替换 10% 的词
  - 随机插入：插入 10% 的同义词
  - 随机交换：交换 10% 的词对
  - 随机删除：以 10% 概率删除词

#### 5. K折交叉验证
- **目标**: 评估模型稳定性，减少过拟合风险
- **使用**: `--use_kfold --n_folds 5`
- **注意**: K折训练时间是单次训练的 K 倍

### 中优先级优化（已实施）

#### 6. 完整停用词表
- **目标**: 提升分词质量，减少噪声词干扰
- **位置**: `backend/data/stopwords.txt`
- **词数**: 400+ 常用停用词
- **自动加载**: TextProcessor 会自动从文件加载

#### 7. 注意力池化层
- **目标**: 替代 [CLS] 标记，更好地聚合序列信息
- **使用**: `--use_attention_pooling --pooling_type attention`
- **池化类型**:
  - `attention`: 单头注意力池化（推荐）
  - `multihead`: 多头注意力池化
  - `mean`: 平均池化
  - `max`: 最大池化

## 训练命令示例

### 基础训练（应用高优先级优化）
```bash
cd backend
python train_sentiment.py \
  --train_file data/train_multiclass.csv \
  --output_dir data/models/roberta-sentiment-v2 \
  --max_length 256 \
  --loss_type focal \
  --focal_gamma 2.0 \
  --use_fgm \
  --use_class_weight \
  --early_stopping \
  --epochs 5 \
  --batch_size 32 \
  --learning_rate 2e-5
```

### K折交叉验证训练
```bash
python train_sentiment.py \
  --train_file data/train_multiclass.csv \
  --output_dir data/models/roberta-sentiment-kfold \
  --max_length 256 \
  --loss_type focal \
  --use_kfold \
  --n_folds 5 \
  --epochs 3
```

### 使用注意力池化训练
```bash
python train_sentiment.py \
  --train_file data/train_multiclass.csv \
  --output_dir data/models/roberta-sentiment-attention \
  --max_length 256 \
  --loss_type focal \
  --use_attention_pooling \
  --pooling_type attention \
  --epochs 5
```

### 完整优化训练（所有功能）
```bash
python train_sentiment.py \
  --train_file data/train_multiclass.csv \
  --output_dir data/models/roberta-sentiment-full \
  --max_length 256 \
  --loss_type focal \
  --focal_gamma 2.0 \
  --use_attention_pooling \
  --pooling_type attention \
  --use_fgm \
  --use_class_weight \
  --early_stopping \
  --patience 3 \
  --epochs 5 \
  --batch_size 32 \
  --learning_rate 2e-5 \
  --warmup_ratio 0.1
```

## 命令行参数完整列表

### 基础参数
- `--train_file`: 训练数据文件路径（必需）
- `--model_name`: 预训练模型名称（默认: hfl/chinese-roberta-wwm-ext）
- `--output_dir`: 模型输出目录（默认: ./data/models/roberta-sentiment）
- `--max_length`: 最大序列长度（默认: 256）
- `--batch_size`: 批次大小（默认: 32）
- `--epochs`: 训练轮数（默认: 5）
- `--learning_rate`: 学习率（默认: 2e-5）
- `--seed`: 随机种子（默认: 42）

### 优化策略开关
- `--use_fgm`: 使用对抗训练（FGM）
- `--use_class_weight`: 使用类别权重平衡
- `--early_stopping`: 使用早停机制
- `--patience`: 早停耐心值（默认: 3）

### 损失函数选择
- `--loss_type`: 损失函数类型（ce/focal/label_smoothing，默认: ce）
- `--focal_gamma`: Focal Loss gamma 参数（默认: 2.0）
- `--label_smoothing`: 标签平滑系数（默认: 0.1）

### 注意力池化
- `--use_attention_pooling`: 使用注意力池化
- `--pooling_type`: 池化类型（attention/mean/max/multihead，默认: attention）

### K折交叉验证
- `--use_kfold`: 使用 K 折交叉验证
- `--n_folds`: K 折数量（默认: 5）

## 运行测试

```bash
# 运行所有测试
cd backend
python -m pytest tests/test_training_optimizations.py -v

# 运行特定测试
python -m pytest tests/test_training_optimizations.py::TestFocalLoss -v
```

## 预期效果

根据实施计划，应用这些优化后预期：

| 优化项 | 预期F1提升 | 训练时间变化 |
|--------|-----------|-------------|
| max_length 256 | +1-2% | +30% |
| Focal Loss | +2-3% | +5% |
| 高级数据增强 | +2-4% | +10% |
| K折交叉验证 | +1-2% (稳定性) | +400% |
| 注意力池化 | +0.5-1% | +5% |
| 停用词表 | +0.5-1% | 0% |

**总体预期**: F1 分数提升 5-10%

## 故障排除

### 1. 内存不足
- 减小 `--batch_size`（如 16 或 8）
- 增加 `--accumulation_steps`（如 2 或 4）
- 减小 `--max_length`（如 128）

### 2. 训练速度慢
- 确保使用 GPU：检查 `torch.cuda.is_available()`
- 减小 `--max_length`
- 关闭 `--use_fgm`（对抗训练会增加 50% 时间）
- 不使用 K 折交叉验证

### 3. 模型效果不佳
- 尝试不同的损失函数（focal vs label_smoothing）
- 调整 `--focal_gamma`（尝试 1.0, 2.0, 3.0）
- 增加训练轮数 `--epochs`
- 使用 K 折交叉验证评估稳定性

### 4. 导入错误
```bash
# 确保在 backend 目录下运行
cd backend

# 检查依赖
pip install -r requirements.txt
pip install -r requirements-ml.txt
```

## 下一步

1. 使用小样本数据测试训练流程
2. 对比不同优化组合的效果
3. 选择最佳配置进行完整训练
4. 评估模型在验证集和测试集上的表现

## 参考资料

- Focal Loss 论文: https://arxiv.org/abs/1708.02002
- EDA 数据增强: https://arxiv.org/abs/1901.11196
- Label Smoothing: https://arxiv.org/abs/1512.00567
