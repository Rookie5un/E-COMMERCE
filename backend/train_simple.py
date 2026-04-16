"""
简化版情感分析训练脚本 - 用于快速测试
使用 bert-base-chinese 模型和小数据集
"""

import pandas as pd
import torch
from torch.optim import AdamW
from torch.utils.data import Dataset, DataLoader
from transformers import BertTokenizer, BertForSequenceClassification
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
from tqdm import tqdm
import os

class SentimentDataset(Dataset):
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

    label_map = {'negative': 0, 'neutral': 1, 'positive': 2}
    texts = df['content'].tolist()
    labels = df['label'].map(label_map).tolist()

    return texts, labels

def train_epoch(model, dataloader, optimizer, device):
    model.train()
    total_loss = 0
    predictions = []
    true_labels = []

    for batch in tqdm(dataloader, desc='Training'):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        labels = batch['label'].to(device)

        optimizer.zero_grad()
        outputs = model(input_ids=input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        preds = torch.argmax(outputs.logits, dim=1)
        predictions.extend(preds.cpu().tolist())
        true_labels.extend(labels.cpu().tolist())

    avg_loss = total_loss / len(dataloader)
    accuracy = accuracy_score(true_labels, predictions)
    return avg_loss, accuracy

def evaluate(model, dataloader, device):
    model.eval()
    predictions = []
    true_labels = []

    with torch.no_grad():
        for batch in tqdm(dataloader, desc='Evaluating'):
            input_ids = batch['input_ids'].to(device)
            attention_mask = batch['attention_mask'].to(device)
            labels = batch['label'].to(device)

            outputs = model(input_ids=input_ids, attention_mask=attention_mask)
            preds = torch.argmax(outputs.logits, dim=1)

            predictions.extend(preds.cpu().tolist())
            true_labels.extend(labels.cpu().tolist())

    accuracy = accuracy_score(true_labels, predictions)
    report = classification_report(true_labels, predictions,
                                   target_names=['negative', 'neutral', 'positive'])
    return accuracy, report

def main():
    # 配置
    train_file = 'data/train_sample.csv'
    model_name = 'bert-base-chinese'
    output_dir = './models/bert-sentiment-simple'
    max_length = 128
    batch_size = 8
    epochs = 3
    learning_rate = 2e-5

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'使用设备: {device}')

    # 加载数据
    print('\n加载数据...')
    texts, labels = load_data(train_file)
    print(f'总样本数: {len(texts)}')

    # 划分数据集
    train_texts, val_texts, train_labels, val_labels = train_test_split(
        texts, labels, test_size=0.2, random_state=42
    )
    print(f'训练集: {len(train_texts)}, 验证集: {len(val_texts)}')

    # 加载模型
    print(f'\n加载模型: {model_name}')
    tokenizer = BertTokenizer.from_pretrained(model_name)
    model = BertForSequenceClassification.from_pretrained(model_name, num_labels=3)
    model.to(device)

    # 创建数据集
    train_dataset = SentimentDataset(train_texts, train_labels, tokenizer, max_length)
    val_dataset = SentimentDataset(val_texts, val_labels, tokenizer, max_length)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=batch_size)

    # 优化器
    optimizer = AdamW(model.parameters(), lr=learning_rate)

    # 训练
    print('\n开始训练...')
    best_accuracy = 0

    for epoch in range(epochs):
        print(f'\nEpoch {epoch + 1}/{epochs}')
        train_loss, train_acc = train_epoch(model, train_loader, optimizer, device)
        print(f'训练 - 损失: {train_loss:.4f}, 准确率: {train_acc:.4f}')

        val_acc, val_report = evaluate(model, val_loader, device)
        print(f'验证 - 准确率: {val_acc:.4f}')
        print('\n分类报告:')
        print(val_report)

        if val_acc > best_accuracy:
            best_accuracy = val_acc
            print(f'\n保存最佳模型 (准确率: {val_acc:.4f})')
            os.makedirs(output_dir, exist_ok=True)
            model.save_pretrained(output_dir)
            tokenizer.save_pretrained(output_dir)

    print(f'\n训练完成！最佳验证准确率: {best_accuracy:.4f}')
    print(f'模型已保存到: {output_dir}')

if __name__ == '__main__':
    main()
