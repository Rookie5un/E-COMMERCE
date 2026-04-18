"""
K折交叉验证训练器

提供稳健的模型评估和训练框架，减少过拟合风险。
"""

import os
import json
import numpy as np
from sklearn.model_selection import StratifiedKFold
from typing import List, Tuple, Callable, Dict, Any
import logging

logger = logging.getLogger(__name__)


class KFoldTrainer:
    """
    K折交叉验证训练器

    使用分层K折交叉验证（StratifiedKFold）保持每折中的类别分布一致。

    Args:
        n_splits: K折数量，默认5
        random_state: 随机种子
        shuffle: 是否打乱数据

    Example:
        >>> kfold_trainer = KFoldTrainer(n_splits=5, random_state=42)
        >>> results = kfold_trainer.train(
        ...     texts=train_texts,
        ...     labels=train_labels,
        ...     train_fn=train_one_fold,
        ...     eval_fn=evaluate_one_fold,
        ...     model_factory=create_model
        ... )
        >>> print(f"平均F1: {results['mean_score']:.4f} ± {results['std_score']:.4f}")
    """

    def __init__(self, n_splits: int = 5, random_state: int = 42, shuffle: bool = True):
        self.n_splits = n_splits
        self.random_state = random_state
        self.shuffle = shuffle
        self.skf = StratifiedKFold(
            n_splits=n_splits,
            shuffle=shuffle,
            random_state=random_state
        )

    def train(self,
              texts: List[str],
              labels: List[int],
              train_fn: Callable,
              eval_fn: Callable,
              model_factory: Callable,
              save_dir: str = None) -> Dict[str, Any]:
        """
        执行K折交叉验证训练

        Args:
            texts: 文本列表
            labels: 标签列表
            train_fn: 训练函数，签名: (model, train_data, fold_idx) -> trained_model
                train_data 格式: (train_texts, train_labels)
            eval_fn: 评估函数，签名: (model, val_data, fold_idx) -> metrics_dict
                val_data 格式: (val_texts, val_labels)
                metrics_dict 必须包含 'f1' 键
            model_factory: 模型工厂函数，签名: () -> model
            save_dir: 保存模型和结果的目录，可选

        Returns:
            {
                'fold_scores': [f1_fold1, f1_fold2, ...],
                'fold_metrics': [metrics_fold1, metrics_fold2, ...],
                'mean_score': float,
                'std_score': float,
                'best_fold': int,
                'models': [model1, model2, ...] (如果 save_dir 为 None)
            }
        """
        texts_array = np.array(texts)
        labels_array = np.array(labels)

        fold_scores = []
        fold_metrics = []
        models = []

        logger.info(f"开始 {self.n_splits} 折交叉验证训练")
        logger.info(f"总样本数: {len(texts)}, 类别分布: {np.bincount(labels_array)}")

        for fold, (train_idx, val_idx) in enumerate(self.skf.split(texts_array, labels_array)):
            logger.info(f"\n{'='*60}")
            logger.info(f"Fold {fold + 1}/{self.n_splits}")
            logger.info(f"{'='*60}")

            # 划分数据
            train_texts = texts_array[train_idx].tolist()
            train_labels = labels_array[train_idx].tolist()
            val_texts = texts_array[val_idx].tolist()
            val_labels = labels_array[val_idx].tolist()

            logger.info(f"训练集: {len(train_texts)} 样本")
            logger.info(f"验证集: {len(val_texts)} 样本")
            logger.info(f"训练集类别分布: {np.bincount(train_labels)}")
            logger.info(f"验证集类别分布: {np.bincount(val_labels)}")

            # 创建新模型
            model = model_factory()

            # 训练
            logger.info(f"开始训练 Fold {fold + 1}...")
            trained_model = train_fn(model, (train_texts, train_labels), fold)

            # 评估
            logger.info(f"评估 Fold {fold + 1}...")
            metrics = eval_fn(trained_model, (val_texts, val_labels), fold)

            # 记录结果
            f1_score = metrics.get('f1', 0.0)
            fold_scores.append(f1_score)
            fold_metrics.append(metrics)

            logger.info(f"Fold {fold + 1} F1: {f1_score:.4f}")
            logger.info(f"Fold {fold + 1} 详细指标: {metrics}")

            # 保存模型
            if save_dir:
                fold_dir = os.path.join(save_dir, f'fold_{fold + 1}')
                os.makedirs(fold_dir, exist_ok=True)

                # 保存模型（假设模型有 save_pretrained 方法）
                if hasattr(trained_model, 'save_pretrained'):
                    trained_model.save_pretrained(fold_dir)
                    logger.info(f"模型已保存到: {fold_dir}")

                # 保存指标
                metrics_file = os.path.join(fold_dir, 'metrics.json')
                with open(metrics_file, 'w', encoding='utf-8') as f:
                    json.dump(metrics, f, ensure_ascii=False, indent=2)
            else:
                models.append(trained_model)

        # 计算统计信息
        mean_score = np.mean(fold_scores)
        std_score = np.std(fold_scores)
        best_fold = int(np.argmax(fold_scores))

        logger.info(f"\n{'='*60}")
        logger.info(f"K折交叉验证完成")
        logger.info(f"{'='*60}")
        logger.info(f"各折F1分数: {[f'{s:.4f}' for s in fold_scores]}")
        logger.info(f"平均F1: {mean_score:.4f} ± {std_score:.4f}")
        logger.info(f"最佳折: Fold {best_fold + 1} (F1: {fold_scores[best_fold]:.4f})")

        results = {
            'fold_scores': fold_scores,
            'fold_metrics': fold_metrics,
            'mean_score': mean_score,
            'std_score': std_score,
            'best_fold': best_fold,
        }

        if not save_dir:
            results['models'] = models

        # 保存汇总结果
        if save_dir:
            summary_file = os.path.join(save_dir, 'kfold_summary.json')
            with open(summary_file, 'w', encoding='utf-8') as f:
                # 移除不可序列化的对象
                serializable_results = {
                    k: v for k, v in results.items()
                    if k != 'models'
                }
                json.dump(serializable_results, f, ensure_ascii=False, indent=2)
            logger.info(f"汇总结果已保存到: {summary_file}")

        return results

    def get_fold_indices(self, texts: List[str], labels: List[int]) -> List[Tuple[np.ndarray, np.ndarray]]:
        """
        获取K折的索引划分（不进行训练）

        Args:
            texts: 文本列表
            labels: 标签列表

        Returns:
            [(train_idx, val_idx), ...] 列表
        """
        texts_array = np.array(texts)
        labels_array = np.array(labels)

        fold_indices = []
        for train_idx, val_idx in self.skf.split(texts_array, labels_array):
            fold_indices.append((train_idx, val_idx))

        return fold_indices


class KFoldEnsemble:
    """
    K折模型集成

    使用K折训练的所有模型进行集成预测。

    Args:
        models: K折训练得到的模型列表
        method: 集成方法，'voting' 或 'averaging'
        weights: 模型权重，可选
    """

    def __init__(self, models: List, method: str = 'voting', weights: List[float] = None):
        self.models = models
        self.method = method
        self.weights = weights or [1.0 / len(models)] * len(models)

        assert len(self.weights) == len(models), "权重数量必须与模型数量一致"
        assert abs(sum(self.weights) - 1.0) < 1e-6, "权重之和必须为1"

    def predict(self, texts: List[str], predict_fn: Callable) -> List[Dict]:
        """
        集成预测

        Args:
            texts: 文本列表
            predict_fn: 预测函数，签名: (model, texts) -> predictions
                predictions 格式: [{'label': str, 'probabilities': {...}}, ...]

        Returns:
            集成后的预测结果列表
        """
        # 收集所有模型的预测
        all_predictions = []
        for model in self.models:
            preds = predict_fn(model, texts)
            all_predictions.append(preds)

        # 集成
        ensemble_results = []
        for i in range(len(texts)):
            # 收集第i个样本的所有预测
            sample_preds = [preds[i] for preds in all_predictions]

            if self.method == 'voting':
                # 硬投票
                labels = [pred['label'] for pred in sample_preds]
                final_label = max(set(labels), key=labels.count)

                # 平均概率
                avg_probs = {}
                for key in sample_preds[0]['probabilities'].keys():
                    avg_probs[key] = np.mean([
                        pred['probabilities'][key] for pred in sample_preds
                    ])

                ensemble_results.append({
                    'label': final_label,
                    'confidence': avg_probs[final_label],
                    'probabilities': avg_probs
                })

            else:  # averaging
                # 加权平均概率
                avg_probs = {}
                for key in sample_preds[0]['probabilities'].keys():
                    avg_probs[key] = np.average([
                        pred['probabilities'][key] for pred in sample_preds
                    ], weights=self.weights)

                final_label = max(avg_probs, key=avg_probs.get)

                ensemble_results.append({
                    'label': final_label,
                    'confidence': avg_probs[final_label],
                    'probabilities': avg_probs
                })

        return ensemble_results
