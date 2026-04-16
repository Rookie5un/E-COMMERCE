"""
模型对比评估脚本

比较不同训练配置的模型性能

使用方法:
python compare_models.py --test_file data/test.csv --model_dirs models/model1 models/model2
"""

import argparse
import pandas as pd
import torch
from transformers import BertTokenizer, BertForSequenceClassification
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
import numpy as np
from tqdm import tqdm
import matplotlib.pyplot as plt
import seaborn as sns

from training_data_utils import LABEL_TO_ID, TRAINING_LABELS, load_labeled_texts


def load_model(model_path, device):
    """加载模型"""
    tokenizer = BertTokenizer.from_pretrained(model_path)
    model = BertForSequenceClassification.from_pretrained(model_path)
    model.to(device)
    model.eval()
    return tokenizer, model


def predict(texts, tokenizer, model, device, batch_size=32, max_length=512):
    """批量预测"""
    predictions = []
    probabilities = []

    for i in tqdm(range(0, len(texts), batch_size), desc='Predicting'):
        batch_texts = texts[i:i + batch_size]

        inputs = tokenizer(
            batch_texts,
            max_length=max_length,
            padding=True,
            truncation=True,
            return_tensors='pt'
        )

        inputs = {k: v.to(device) for k, v in inputs.items()}

        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)
            preds = torch.argmax(probs, dim=1)

        predictions.extend(preds.cpu().tolist())
        probabilities.extend(probs.cpu().tolist())

    return predictions, probabilities


def evaluate_model(model_path, test_texts, test_labels, device):
    """评估单个模型"""
    print(f"\n{'='*60}")
    print(f"评估模型: {model_path}")
    print(f"{'='*60}")

    # 加载模型
    tokenizer, model = load_model(model_path, device)

    # 预测
    predictions, probabilities = predict(test_texts, tokenizer, model, device)

    # 计算指标
    accuracy = accuracy_score(test_labels, predictions)
    f1_macro = f1_score(test_labels, predictions, average='macro')
    f1_weighted = f1_score(test_labels, predictions, average='weighted')

    # 分类报告
    report = classification_report(
        test_labels,
        predictions,
        labels=list(LABEL_TO_ID.values()),
        target_names=list(TRAINING_LABELS),
        digits=4
    )

    # 混淆矩阵
    cm = confusion_matrix(test_labels, predictions)

    print(f"\n准确率: {accuracy:.4f}")
    print(f"F1 (macro): {f1_macro:.4f}")
    print(f"F1 (weighted): {f1_weighted:.4f}")
    print(f"\n分类报告:")
    print(report)
    print(f"\n混淆矩阵:")
    print(cm)

    # 计算每个类别的置信度
    probs_array = np.array(probabilities)
    avg_confidence = {}
    for i, label_name in enumerate(TRAINING_LABELS):
        mask = np.array(test_labels) == i
        if mask.sum() > 0:
            avg_conf = probs_array[mask, i].mean()
            avg_confidence[label_name] = avg_conf
            print(f"{label_name} 平均置信度: {avg_conf:.4f}")

    return {
        'model_path': model_path,
        'accuracy': accuracy,
        'f1_macro': f1_macro,
        'f1_weighted': f1_weighted,
        'confusion_matrix': cm,
        'predictions': predictions,
        'probabilities': probabilities,
        'avg_confidence': avg_confidence
    }


def plot_comparison(results, output_path='model_comparison.png'):
    """绘制对比图"""
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))

    # 1. 准确率和F1对比
    model_names = [r['model_path'].split('/')[-1] for r in results]
    accuracies = [r['accuracy'] for r in results]
    f1_scores = [r['f1_macro'] for r in results]

    x = np.arange(len(model_names))
    width = 0.35

    axes[0, 0].bar(x - width/2, accuracies, width, label='Accuracy', alpha=0.8)
    axes[0, 0].bar(x + width/2, f1_scores, width, label='F1 (macro)', alpha=0.8)
    axes[0, 0].set_xlabel('Model')
    axes[0, 0].set_ylabel('Score')
    axes[0, 0].set_title('Accuracy and F1 Score Comparison')
    axes[0, 0].set_xticks(x)
    axes[0, 0].set_xticklabels(model_names, rotation=45, ha='right')
    axes[0, 0].legend()
    axes[0, 0].grid(axis='y', alpha=0.3)

    # 2. 混淆矩阵（第一个模型）
    cm = results[0]['confusion_matrix']
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=axes[0, 1],
                xticklabels=['neg', 'neu', 'pos'],
                yticklabels=['neg', 'neu', 'pos'])
    axes[0, 1].set_title(f'Confusion Matrix - {model_names[0]}')
    axes[0, 1].set_ylabel('True Label')
    axes[0, 1].set_xlabel('Predicted Label')

    # 3. 各类别F1对比
    if len(results) > 1:
        cm2 = results[1]['confusion_matrix']
        sns.heatmap(cm2, annot=True, fmt='d', cmap='Greens', ax=axes[1, 0],
                    xticklabels=['neg', 'neu', 'pos'],
                    yticklabels=['neg', 'neu', 'pos'])
        axes[1, 0].set_title(f'Confusion Matrix - {model_names[1]}')
        axes[1, 0].set_ylabel('True Label')
        axes[1, 0].set_xlabel('Predicted Label')
    else:
        axes[1, 0].axis('off')

    # 4. 置信度对比
    confidence_data = []
    for result in results:
        for label, conf in result['avg_confidence'].items():
            confidence_data.append({
                'Model': result['model_path'].split('/')[-1],
                'Label': label,
                'Confidence': conf
            })

    df_conf = pd.DataFrame(confidence_data)
    df_pivot = df_conf.pivot(index='Label', columns='Model', values='Confidence')
    df_pivot.plot(kind='bar', ax=axes[1, 1], alpha=0.8)
    axes[1, 1].set_title('Average Confidence by Class')
    axes[1, 1].set_ylabel('Confidence')
    axes[1, 1].set_xlabel('Label')
    axes[1, 1].legend(title='Model', bbox_to_anchor=(1.05, 1), loc='upper left')
    axes[1, 1].grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\n对比图已保存到: {output_path}")


def main():
    parser = argparse.ArgumentParser(description='模型对比评估')
    parser.add_argument('--test_file', type=str, required=True, help='测试数据文件')
    parser.add_argument('--model_dirs', type=str, nargs='+', required=True, help='模型目录列表')
    parser.add_argument('--output', type=str, default='model_comparison.png', help='输出图片路径')

    args = parser.parse_args()

    # 设置设备
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'使用设备: {device}')

    # 加载测试数据
    print(f'\n加载测试数据: {args.test_file}')
    test_texts, test_labels, dataset_summary = load_labeled_texts(
        args.test_file,
        require_all_labels=True,
        min_samples_per_label=1,
        min_content_length=5,
    )

    print(f'测试样本数: {len(test_texts)}')
    print(f'类别分布: {dataset_summary.label_counts}')

    # 评估每个模型
    results = []
    for model_dir in args.model_dirs:
        result = evaluate_model(model_dir, test_texts, test_labels, device)
        results.append(result)

    # 对比总结
    print(f"\n{'='*60}")
    print("对比总结")
    print(f"{'='*60}")

    comparison_df = pd.DataFrame([
        {
            'Model': r['model_path'].split('/')[-1],
            'Accuracy': f"{r['accuracy']:.4f}",
            'F1 (macro)': f"{r['f1_macro']:.4f}",
            'F1 (weighted)': f"{r['f1_weighted']:.4f}"
        }
        for r in results
    ])

    print(comparison_df.to_string(index=False))

    # 找出最佳模型
    best_model = max(results, key=lambda x: x['f1_macro'])
    print(f"\n🏆 最佳模型: {best_model['model_path']}")
    print(f"   F1 (macro): {best_model['f1_macro']:.4f}")
    print(f"   准确率: {best_model['accuracy']:.4f}")

    # 绘制对比图
    if len(results) > 0:
        plot_comparison(results, args.output)


if __name__ == '__main__':
    main()
