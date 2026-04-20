"""
中评判断后处理模块

通过后处理策略提升中评判断准确率。
"""

import numpy as np
from typing import Dict, List, Tuple


class NeutralPostProcessor:
    """
    中评后处理器

    核心策略：
    1. 动态阈值调整：根据概率分布动态调整中评判断阈值
    2. 混合情感检测：检测正负混合的评论，判定为中评
    3. 置信度校准：对低置信度预测进行二次判断
    """

    def __init__(
        self,
        neutral_threshold_low: float = 0.35,
        neutral_threshold_high: float = 0.65,
        mixed_sentiment_threshold: float = 0.25,
        confidence_threshold: float = 0.5
    ):
        """
        Args:
            neutral_threshold_low: 中评下界阈值
            neutral_threshold_high: 中评上界阈值
            mixed_sentiment_threshold: 混合情感阈值（正负概率都>此值则判为中评）
            confidence_threshold: 置信度阈值（低于此值需要二次判断）
        """
        self.neutral_threshold_low = neutral_threshold_low
        self.neutral_threshold_high = neutral_threshold_high
        self.mixed_sentiment_threshold = mixed_sentiment_threshold
        self.confidence_threshold = confidence_threshold

    def process(self, probabilities: Dict[str, float]) -> Dict[str, any]:
        """
        后处理单个预测结果

        Args:
            probabilities: {'negative': 0.2, 'neutral': 0.3, 'positive': 0.5}

        Returns:
            {
                'label': str,
                'confidence': float,
                'probabilities': dict,
                'is_adjusted': bool,
                'adjustment_reason': str
            }
        """
        neg_prob = probabilities['negative']
        neu_prob = probabilities['neutral']
        pos_prob = probabilities['positive']

        # 原始预测
        original_label = max(probabilities, key=probabilities.get)
        original_confidence = probabilities[original_label]

        # 策略1: 混合情感检测
        if self._is_mixed_sentiment(neg_prob, pos_prob):
            return {
                'label': 'neutral',
                'confidence': neu_prob,
                'probabilities': probabilities,
                'is_adjusted': True,
                'adjustment_reason': f'混合情感检测(neg={neg_prob:.2f}, pos={pos_prob:.2f})'
            }

        # 策略2: 边界样本检测
        if self._is_boundary_sample(neg_prob, neu_prob, pos_prob):
            return {
                'label': 'neutral',
                'confidence': neu_prob,
                'probabilities': probabilities,
                'is_adjusted': True,
                'adjustment_reason': f'边界样本检测(概率分布较均匀)'
            }

        # 策略3: 低置信度调整
        if original_confidence < self.confidence_threshold:
            adjusted_label = self._adjust_low_confidence(
                neg_prob, neu_prob, pos_prob, original_label
            )
            if adjusted_label != original_label:
                return {
                    'label': adjusted_label,
                    'confidence': probabilities[adjusted_label],
                    'probabilities': probabilities,
                    'is_adjusted': True,
                    'adjustment_reason': f'低置信度调整(原={original_label}, 置信度={original_confidence:.2f})'
                }

        # 无需调整
        return {
            'label': original_label,
            'confidence': original_confidence,
            'probabilities': probabilities,
            'is_adjusted': False,
            'adjustment_reason': None
        }

    def _is_mixed_sentiment(self, neg_prob: float, pos_prob: float) -> bool:
        """
        检测是否为混合情感

        如果正面和负面概率都较高，判定为中评
        """
        return (
            neg_prob >= self.mixed_sentiment_threshold and
            pos_prob >= self.mixed_sentiment_threshold
        )

    def _is_boundary_sample(
        self,
        neg_prob: float,
        neu_prob: float,
        pos_prob: float
    ) -> bool:
        """
        检测是否为边界样本

        如果三个类别概率都比较接近，判定为中评
        """
        probs = [neg_prob, neu_prob, pos_prob]
        max_prob = max(probs)
        min_prob = min(probs)

        # 如果最大和最小概率差距小于0.2，认为是边界样本
        return (max_prob - min_prob) < 0.2

    def _adjust_low_confidence(
        self,
        neg_prob: float,
        neu_prob: float,
        pos_prob: float,
        original_label: str
    ) -> str:
        """
        低置信度样本调整

        如果原始预测置信度低，且中评概率不是最低，考虑调整为中评
        """
        probs = {
            'negative': neg_prob,
            'neutral': neu_prob,
            'positive': pos_prob
        }

        # 如果中评概率排第二，且与第一名差距不大，调整为中评
        sorted_probs = sorted(probs.items(), key=lambda x: x[1], reverse=True)

        if sorted_probs[1][0] == 'neutral':
            # 中评排第二
            if sorted_probs[0][1] - sorted_probs[1][1] < 0.15:
                # 与第一名差距小于0.15
                return 'neutral'

        return original_label

    def batch_process(
        self,
        batch_probabilities: List[Dict[str, float]]
    ) -> List[Dict[str, any]]:
        """
        批量后处理

        Args:
            batch_probabilities: [{'negative': 0.2, 'neutral': 0.3, 'positive': 0.5}, ...]

        Returns:
            后处理结果列表
        """
        return [self.process(probs) for probs in batch_probabilities]


class ThresholdOptimizer:
    """
    阈值优化器

    通过验证集自动寻找最优的中评判断阈值
    """

    def __init__(self):
        self.best_thresholds = None

    def optimize(
        self,
        val_probabilities: List[Dict[str, float]],
        val_labels: List[str],
        metric: str = 'f1'
    ) -> Dict[str, float]:
        """
        优化阈值

        Args:
            val_probabilities: 验证集概率
            val_labels: 验证集真实标签
            metric: 优化指标 ('f1', 'accuracy', 'recall')

        Returns:
            最优阈值配置
        """
        from sklearn.metrics import f1_score, accuracy_score, recall_score

        best_score = 0
        best_config = None

        # 网格搜索
        for neutral_low in np.arange(0.25, 0.45, 0.05):
            for neutral_high in np.arange(0.55, 0.75, 0.05):
                for mixed_threshold in np.arange(0.20, 0.35, 0.05):
                    for conf_threshold in np.arange(0.40, 0.60, 0.05):

                        # 创建后处理器
                        processor = NeutralPostProcessor(
                            neutral_threshold_low=neutral_low,
                            neutral_threshold_high=neutral_high,
                            mixed_sentiment_threshold=mixed_threshold,
                            confidence_threshold=conf_threshold
                        )

                        # 后处理
                        results = processor.batch_process(val_probabilities)
                        predictions = [r['label'] for r in results]

                        # 计算指标
                        if metric == 'f1':
                            score = f1_score(
                                val_labels,
                                predictions,
                                labels=['negative', 'neutral', 'positive'],
                                average='macro'
                            )
                        elif metric == 'accuracy':
                            score = accuracy_score(val_labels, predictions)
                        elif metric == 'recall':
                            # 专注于中评的召回率
                            score = recall_score(
                                val_labels,
                                predictions,
                                labels=['neutral'],
                                average='macro'
                            )

                        if score > best_score:
                            best_score = score
                            best_config = {
                                'neutral_threshold_low': neutral_low,
                                'neutral_threshold_high': neutral_high,
                                'mixed_sentiment_threshold': mixed_threshold,
                                'confidence_threshold': conf_threshold,
                                'score': score
                            }

        self.best_thresholds = best_config
        return best_config


class EnsembleNeutralClassifier:
    """
    集成中评分类器

    结合多个策略进行投票，提升中评判断准确率
    """

    def __init__(self):
        self.strategies = [
            self._strategy_probability_based,
            self._strategy_mixed_sentiment,
            self._strategy_boundary_detection,
        ]

    def predict(self, probabilities: Dict[str, float]) -> str:
        """
        集成预测

        Args:
            probabilities: {'negative': 0.2, 'neutral': 0.3, 'positive': 0.5}

        Returns:
            预测标签
        """
        votes = []

        for strategy in self.strategies:
            vote = strategy(probabilities)
            votes.append(vote)

        # 多数投票
        from collections import Counter
        vote_counts = Counter(votes)
        return vote_counts.most_common(1)[0][0]

    def _strategy_probability_based(self, probs: Dict[str, float]) -> str:
        """策略1: 基于概率的直接预测"""
        return max(probs, key=probs.get)

    def _strategy_mixed_sentiment(self, probs: Dict[str, float]) -> str:
        """策略2: 混合情感检测"""
        if probs['negative'] > 0.25 and probs['positive'] > 0.25:
            return 'neutral'
        return max(probs, key=probs.get)

    def _strategy_boundary_detection(self, probs: Dict[str, float]) -> str:
        """策略3: 边界检测"""
        values = list(probs.values())
        if max(values) - min(values) < 0.2:
            return 'neutral'
        return max(probs, key=probs.get)


def calibrate_probabilities(
    probabilities: np.ndarray,
    temperature: float = 1.5
) -> np.ndarray:
    """
    温度缩放校准概率

    对于中评判断，可以使用温度缩放使概率分布更平滑，
    避免模型过于自信。

    Args:
        probabilities: (batch_size, 3) 概率矩阵
        temperature: 温度参数，>1使分布更平滑，<1使分布更尖锐

    Returns:
        校准后的概率
    """
    # 转换为logits
    logits = np.log(probabilities + 1e-8)

    # 温度缩放
    scaled_logits = logits / temperature

    # 转换回概率
    exp_logits = np.exp(scaled_logits)
    calibrated_probs = exp_logits / exp_logits.sum(axis=-1, keepdims=True)

    return calibrated_probs
