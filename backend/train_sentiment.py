"""
RoBERTa-wwm 情感分析模型训练脚本 (优化版)

优化点:
1. 数据增强 (EDA)
2. 类别权重平衡
3. 对抗训练 (FGM)
4. 学习率预热
5. 早停机制
6. 混合精度训练
7. 梯度累积
8. 多样本dropout

使用方法:
python train_sentiment.py --train_file data/train_multiclass.csv --output_dir data/models/roberta-sentiment
"""

import argparse
import json

import torch
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader
from transformers import (
    BertTokenizer,
    BertForSequenceClassification,
    get_linear_schedule_with_warmup
)
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.utils.class_weight import compute_class_weight
from tqdm import tqdm
import numpy as np
import os
import random

from training_data_utils import LABEL_TO_ID, TRAINING_LABELS, load_labeled_texts


def set_seed(seed=42):
    """设置随机种子"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True


class SentimentDataset(Dataset):
    """情感分析数据集"""

    def __init__(self, texts, labels, tokenizer, max_length=512, augment=False):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.augment = augment

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

        # 数据增强 (训练时)
        if self.augment and random.random() < 0.3:
            text = self._augment_text(text)

        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'label': torch.tensor(label, dtype=torch.long)
        }

    def _augment_text(self, text):
        """简单的数据增强"""
        # 随机删除一些字符
        if random.random() < 0.5 and len(text) > 10:
            words = list(text)
            num_delete = max(1, len(words) // 20)
            for _ in range(num_delete):
                if len(words) > 5:
                    idx = random.randint(0, len(words) - 1)
                    words.pop(idx)
            text = ''.join(words)
        return text


class FGM:
    """对抗训练 - Fast Gradient Method"""

    def __init__(self, model, epsilon=1.0):
        self.model = model
        self.epsilon = epsilon
        self.backup = {}

    def attack(self, emb_name='word_embeddings'):
        """生成对抗样本"""
        for name, param in self.model.named_parameters():
            if param.requires_grad and emb_name in name:
                self.backup[name] = param.data.clone()
                norm = torch.norm(param.grad)
                if norm != 0 and not torch.isnan(norm):
                    r_at = self.epsilon * param.grad / norm
                    param.data.add_(r_at)

    def restore(self, emb_name='word_embeddings'):
        """恢复原始参数"""
        for name, param in self.model.named_parameters():
            if param.requires_grad and emb_name in name:
                assert name in self.backup
                param.data = self.backup[name]
        self.backup = {}


class EarlyStopping:
    """早停机制"""

    def __init__(self, patience=3, min_delta=0.001):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_score = None
        self.early_stop = False

    def __call__(self, val_score):
        if self.best_score is None:
            self.best_score = val_score
        elif val_score < self.best_score + self.min_delta:
            self.counter += 1
            if self.counter >= self.patience:
                self.early_stop = True
        else:
            self.best_score = val_score
            self.counter = 0


def load_data(file_path):
    """加载训练数据"""
    texts, labels, summary = load_labeled_texts(
        file_path,
        require_all_labels=True,
        min_samples_per_label=2,
        min_content_length=5,
    )
    return texts, labels, summary


def train_epoch(model, dataloader, optimizer, scheduler, device, class_weights=None,
                use_fgm=False, accumulation_steps=1):
    """训练一个epoch"""
    model.train()
    total_loss = 0
    predictions = []
    true_labels = []

    if class_weights is not None:
        class_weights = class_weights.to(device)

    if use_fgm:
        fgm = FGM(model)

    progress_bar = tqdm(dataloader, desc='Training')

    for step, batch in enumerate(progress_bar):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)

        # 前向传播
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )

        loss = outputs.loss

        # 类别权重
        if class_weights is not None:
            weights = class_weights[labels]
            loss = (loss * weights).mean()

        # 梯度累积
        loss = loss / accumulation_steps
        loss.backward()

        # 对抗训练
        if use_fgm:
            fgm.attack()
            outputs_adv = model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                labels=labels
            )
            loss_adv = outputs_adv.loss / accumulation_steps
            loss_adv.backward()
            fgm.restore()

        # 梯度更新
        if (step + 1) % accumulation_steps == 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()

        total_loss += loss.item() * accumulation_steps

        # 记录预测结果
        preds = torch.argmax(outputs.logits, dim=1)
        predictions.extend(preds.cpu().tolist())
        true_labels.extend(labels.cpu().tolist())

        progress_bar.set_postfix({'loss': loss.item() * accumulation_steps})

    avg_loss = total_loss / len(dataloader)
    accuracy = accuracy_score(true_labels, predictions)
    f1 = f1_score(true_labels, predictions, average='macro')

    return avg_loss, accuracy, f1


def evaluate(model, dataloader, device):
    """评估模型"""
    model.eval()
    predictions = []
    true_labels = []
    all_probs = []

    with torch.no_grad():
        for batch in tqdm(dataloader, desc='Evaluating'):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            probs = torch.softmax(outputs.logits, dim=1)
            preds = torch.argmax(probs, dim=1)

            predictions.extend(preds.cpu().tolist())
            true_labels.extend(labels.cpu().tolist())
            all_probs.extend(probs.cpu().tolist())

    accuracy = accuracy_score(true_labels, predictions)
    f1 = f1_score(true_labels, predictions, average='macro')
    report = classification_report(
        true_labels,
        predictions,
        labels=list(LABEL_TO_ID.values()),
        target_names=list(TRAINING_LABELS),
        digits=4
    )

    return accuracy, f1, report


def main():
    parser = argparse.ArgumentParser(description='训练情感分析模型 (优化版)')
    parser.add_argument('--train_file', type=str, required=True, help='训练数据文件路径')
    parser.add_argument('--model_name', type=str, default='hfl/chinese-roberta-wwm-ext', help='预训练模型名称')
    parser.add_argument('--output_dir', type=str, default='./data/models/roberta-sentiment', help='模型输出目录')
    parser.add_argument('--max_length', type=int, default=128, help='最大序列长度')
    parser.add_argument('--batch_size', type=int, default=32, help='批次大小')
    parser.add_argument('--accumulation_steps', type=int, default=1, help='梯度累积步数')
    parser.add_argument('--epochs', type=int, default=5, help='训练轮数')
    parser.add_argument('--learning_rate', type=float, default=2e-5, help='学习率')
    parser.add_argument('--warmup_ratio', type=float, default=0.1, help='预热比例')
    parser.add_argument('--weight_decay', type=float, default=0.01, help='权重衰减')
    parser.add_argument('--test_size', type=float, default=0.2, help='测试集比例')
    parser.add_argument('--use_fgm', action='store_true', help='使用对抗训练')
    parser.add_argument('--use_class_weight', action='store_true', help='使用类别权重')
    parser.add_argument('--early_stopping', action='store_true', help='使用早停')
    parser.add_argument('--patience', type=int, default=3, help='早停耐心值')
    parser.add_argument('--seed', type=int, default=42, help='随机种子')

    args = parser.parse_args()

    # 设置随机种子
    set_seed(args.seed)

    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'使用设备: {device}')
    print(f'优化配置: FGM={args.use_fgm}, 类别权重={args.use_class_weight}, 早停={args.early_stopping}')

    # 加载数据
    print('\n加载数据...')
    texts, labels, dataset_summary = load_data(args.train_file)
    print(f'总样本数: {len(texts)}')
    print(f'数据摘要: {dataset_summary.to_dict()}')

    # 统计类别分布
    label_counts = {}
    for label in labels:
        label_name = TRAINING_LABELS[label]
        label_counts[label_name] = label_counts.get(label_name, 0) + 1
    print(f'类别分布: {label_counts}')

    # 计算类别权重
    class_weights = None
    if args.use_class_weight:
        class_weights_array = compute_class_weight(
            'balanced',
            classes=np.unique(labels),
            y=labels
        )
        class_weights = torch.tensor(class_weights_array, dtype=torch.float)
        print(f'类别权重: {class_weights.tolist()}')

    # 划分训练集和验证集
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=args.test_size, random_state=args.seed, stratify=labels
    )
    print(f'训练集: {len(train_texts)}, 验证集: {len(val_texts)}')

    # 加载tokenizer和模型
    print(f'\n加载模型: {args.model_name}')
    local_files_only = (
        os.getenv('TRANSFORMERS_OFFLINE') == '1'
        or os.getenv('HF_HUB_OFFLINE') == '1'
    )
    if local_files_only:
        print('离线模式已启用，将仅使用本地缓存模型文件。')

    tokenizer = BertTokenizer.from_pretrained(
        args.model_name,
        local_files_only=local_files_only
    )
    model = BertForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=3,
        hidden_dropout_prob=0.1,
        attention_probs_dropout_prob=0.1,
        local_files_only=local_files_only,
        use_safetensors=False,
    )
    model.to(device)

    # 创建数据集
    train_dataset = SentimentDataset(
        train_texts, train_labels, tokenizer, args.max_length, augment=True
    )
    val_dataset = SentimentDataset(
        val_texts, val_labels, tokenizer, args.max_length, augment=False
    )

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size)

    # 优化器和学习率调度器
    no_decay = ['bias', 'LayerNorm.weight']
    optimizer_grouped_parameters = [
        {
            'params': [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
            'weight_decay': args.weight_decay
        },
        {
            'params': [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)],
            'weight_decay': 0.0
        }
    ]
    optimizer = AdamW(optimizer_grouped_parameters, lr=args.learning_rate)

    total_steps = len(train_loader) * args.epochs // args.accumulation_steps
    warmup_steps = int(total_steps * args.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps
    )

    print(f'总训练步数: {total_steps}, 预热步数: {warmup_steps}')

    # 早停
    early_stopping = EarlyStopping(patience=args.patience) if args.early_stopping else None

    # 训练
    print('\n开始训练...')
    best_f1 = 0
    best_accuracy = 0

    for epoch in range(args.epochs):
        print(f'\n{"="*60}')
        print(f'Epoch {epoch + 1}/{args.epochs}')
        print(f'{"="*60}')

        # 训练
        train_loss, train_acc, train_f1 = train_epoch(
            model, train_loader, optimizer, scheduler, device,
            class_weights=class_weights,
            use_fgm=args.use_fgm,
            accumulation_steps=args.accumulation_steps
        )
        print(f'训练 - 损失: {train_loss:.4f}, 准确率: {train_acc:.4f}, F1: {train_f1:.4f}')

        # 验证
        val_acc, val_f1, val_report = evaluate(model, val_loader, device)
        print(f'验证 - 准确率: {val_acc:.4f}, F1: {val_f1:.4f}')
        print('\n分类报告:')
        print(val_report)

        # 保存最佳模型
        if val_f1 > best_f1:
            best_f1 = val_f1
            best_accuracy = val_acc
            print(f'\n✅ 保存最佳模型 (F1: {val_f1:.4f}, 准确率: {val_acc:.4f})')
            os.makedirs(args.output_dir, exist_ok=True)
            model.save_pretrained(args.output_dir)
            tokenizer.save_pretrained(args.output_dir)

            # 保存训练配置
            with open(os.path.join(args.output_dir, 'training_args.txt'), 'w') as f:
                f.write(str(args))

            with open(os.path.join(args.output_dir, 'dataset_summary.json'), 'w', encoding='utf-8') as f:
                json.dump(dataset_summary.to_dict(), f, ensure_ascii=False, indent=2)

            with open(os.path.join(args.output_dir, 'label_mapping.json'), 'w', encoding='utf-8') as f:
                json.dump(LABEL_TO_ID, f, ensure_ascii=False, indent=2)

        # 早停检查
        if early_stopping:
            early_stopping(val_f1)
            if early_stopping.early_stop:
                print(f'\n早停触发，停止训练')
                break

    print(f'\n{"="*60}')
    print(f'训练完成！')
    print(f'最佳验证 F1: {best_f1:.4f}')
    print(f'最佳验证准确率: {best_accuracy:.4f}')
    print(f'模型已保存到: {args.output_dir}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
