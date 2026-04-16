"""
遗留二分类情感分析训练脚本 (positive/negative)

仅用于历史对照实验，不作为当前生产三分类训练主入口。
"""

import argparse
import pandas as pd
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
from tqdm import tqdm
import numpy as np
import os
import random


def set_seed(seed=42):
    """设置随机种子"""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


class SentimentDataset(Dataset):
    """情感分析数据集"""

    def __init__(self, texts, labels, tokenizer, max_length=128):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        label = self.labels[idx]

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


def load_data(file_path):
    """加载训练数据"""
    df = pd.read_csv(file_path)
    df = df.dropna(subset=['content', 'label'])
    df['content'] = df['content'].astype(str).str.strip()
    df = df[df['content'].str.len() > 0]

    # 二分类标签映射
    label_map = {
        'negative': 0,
        'positive': 1
    }

    texts = df['content'].tolist()
    labels = df['label'].map(label_map).tolist()

    return texts, labels


def train_epoch(model, dataloader, optimizer, scheduler, device):
    """训练一个epoch"""
    model.train()
    total_loss = 0
    predictions = []
    true_labels = []

    progress_bar = tqdm(dataloader, desc='Training')

    for batch in progress_bar:
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)

        optimizer.zero_grad()
        outputs = model(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels
        )

        loss = outputs.loss
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()

        total_loss += loss.item()
        preds = torch.argmax(outputs.logits, dim=1)
        predictions.extend(preds.cpu().tolist())
        true_labels.extend(labels.cpu().tolist())

        progress_bar.set_postfix({'loss': loss.item()})

    avg_loss = total_loss / len(dataloader)
    accuracy = accuracy_score(true_labels, predictions)
    f1 = f1_score(true_labels, predictions, average='binary')

    return avg_loss, accuracy, f1


def evaluate(model, dataloader, device):
    """评估模型"""
    model.eval()
    predictions = []
    true_labels = []

    with torch.no_grad():
        for batch in tqdm(dataloader, desc='Evaluating'):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)

            outputs = model(
                input_ids=input_ids,
                attention_mask=attention_mask
            )

            preds = torch.argmax(outputs.logits, dim=1)
            predictions.extend(preds.cpu().tolist())
            true_labels.extend(labels.cpu().tolist())

    accuracy = accuracy_score(true_labels, predictions)
    f1 = f1_score(true_labels, predictions, average='binary')
    report = classification_report(
        true_labels,
        predictions,
        labels=[0, 1],
        target_names=['negative', 'positive'],
        digits=4
    )

    return accuracy, f1, report


def main():
    parser = argparse.ArgumentParser(description='训练二分类情感分析模型（遗留对照脚本）')
    parser.add_argument('--train_file', type=str, default='data/train_binary_base.csv', help='训练数据文件路径')
    parser.add_argument('--model_name', type=str, default='bert-base-chinese', help='预训练模型名称')
    parser.add_argument('--output_dir', type=str, default='./models/sentiment-binary', help='模型输出目录')
    parser.add_argument('--max_length', type=int, default=128, help='最大序列长度')
    parser.add_argument('--batch_size', type=int, default=32, help='批次大小')
    parser.add_argument('--epochs', type=int, default=3, help='训练轮数')
    parser.add_argument('--learning_rate', type=float, default=2e-5, help='学习率')
    parser.add_argument('--warmup_ratio', type=float, default=0.1, help='预热比例')
    parser.add_argument('--test_size', type=float, default=0.1, help='测试集比例')
    parser.add_argument('--seed', type=int, default=42, help='随机种子')

    args = parser.parse_args()

    # 设置随机种子
    set_seed(args.seed)

    print('警告: train_binary.py 仅保留给历史对照实验，正式训练请使用 train_sentiment.py。')

    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'使用设备: {device}')

    # 加载数据
    print('\n加载数据...')
    texts, labels = load_data(args.train_file)
    print(f'总样本数: {len(texts)}')

    # 统计类别分布
    label_counts = {'negative': labels.count(0), 'positive': labels.count(1)}
    print(f'类别分布: {label_counts}')

    # 划分训练集和验证集
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=args.test_size, random_state=args.seed, stratify=labels
    )
    print(f'训练集: {len(train_texts)}, 验证集: {len(val_texts)}')

    # 加载tokenizer和模型
    print(f'\n加载模型: {args.model_name}')
    tokenizer = BertTokenizer.from_pretrained(args.model_name)
    model = BertForSequenceClassification.from_pretrained(
        args.model_name,
        num_labels=2
    )
    model.to(device)

    # 创建数据集
    train_dataset = SentimentDataset(train_texts, train_labels, tokenizer, args.max_length)
    val_dataset = SentimentDataset(val_texts, val_labels, tokenizer, args.max_length)

    train_loader = DataLoader(train_dataset, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=args.batch_size)

    # 优化器和学习率调度器
    optimizer = AdamW(model.parameters(), lr=args.learning_rate)
    total_steps = len(train_loader) * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps
    )

    print(f'总训练步数: {total_steps}, 预热步数: {warmup_steps}')

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
            model, train_loader, optimizer, scheduler, device
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

    print(f'\n{"="*60}')
    print(f'训练完成！')
    print(f'最佳验证 F1: {best_f1:.4f}')
    print(f'最佳验证准确率: {best_accuracy:.4f}')
    print(f'模型已保存到: {args.output_dir}')
    print(f'{"="*60}')


if __name__ == '__main__':
    main()
