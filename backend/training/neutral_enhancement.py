"""
中评样本增强模块

针对中评（neutral）判断不准确的问题，提供专门的数据增强和样本生成策略。

中评难点：
1. 边界模糊：介于正负之间，特征不明显
2. 样本稀少：通常比正负评少很多
3. 表达多样：既有正面又有负面、平淡陈述、有保留的评价等
"""

import random
import jieba
from typing import List, Tuple
import numpy as np


class NeutralSampleEnhancer:
    """中评样本增强器"""

    def __init__(self):
        # 中评的典型模式
        self.neutral_patterns = {
            # 1. 正负混合型："XX好，但是YY不好"
            'mixed': {
                'templates': [
                    '{positive}，但是{negative}',
                    '{positive}，不过{negative}',
                    '{negative}，但{positive}',
                    '{positive}，就是{negative}',
                ],
                'positive_phrases': ['质量不错', '外观好看', '速度还行', '价格合理', '包装精美'],
                'negative_phrases': ['续航一般', '有点贵', '屏幕偏小', '发热明显', '音质普通']
            },

            # 2. 平淡陈述型："还行"、"一般"、"凑合"
            'plain': {
                'keywords': ['还行', '一般', '凑合', '还可以', '马马虎虎', '中规中矩',
                           '没什么特别', '普普通通', '说得过去', '不好不坏'],
                'templates': [
                    '整体{keyword}',
                    '用着{keyword}',
                    '{keyword}吧',
                    '感觉{keyword}',
                ]
            },

            # 3. 有保留的评价："还不错，但不算特别好"
            'reserved': {
                'templates': [
                    '{positive}，但不算{superlative}',
                    '{positive}，谈不上{superlative}',
                    '比较{positive}，不过也就{level}',
                ],
                'positive': ['不错', '可以', '满意', '好用'],
                'superlative': ['特别好', '很优秀', '完美', '惊艳'],
                'level': ['这样', '那样', '一般水平']
            },

            # 4. 期望不匹配型："没有想象中好"
            'expectation': {
                'templates': [
                    '没有{expectation}',
                    '不如{expectation}',
                    '和{expectation}有差距',
                ],
                'expectation': ['想象中好', '预期的好', '宣传的那么好', '评价说的那么好']
            }
        }

        # 中评的弱化词和限定词
        self.neutral_modifiers = [
            '还', '比较', '稍微', '有点', '算是', '基本', '大致',
            '相对', '总体', '整体来说', '勉强', '尚可'
        ]

    def generate_synthetic_neutral(self, num_samples: int = 100) -> List[str]:
        """
        生成合成的中评样本

        用于扩充训练集中的中评数据

        Args:
            num_samples: 生成样本数量

        Returns:
            合成的中评文本列表
        """
        samples = []

        for _ in range(num_samples):
            pattern_type = random.choice(['mixed', 'plain', 'reserved', 'expectation'])

            if pattern_type == 'mixed':
                template = random.choice(self.neutral_patterns['mixed']['templates'])
                positive = random.choice(self.neutral_patterns['mixed']['positive_phrases'])
                negative = random.choice(self.neutral_patterns['mixed']['negative_phrases'])
                text = template.format(positive=positive, negative=negative)

            elif pattern_type == 'plain':
                template = random.choice(self.neutral_patterns['plain']['templates'])
                keyword = random.choice(self.neutral_patterns['plain']['keywords'])
                text = template.format(keyword=keyword)

            elif pattern_type == 'reserved':
                template = random.choice(self.neutral_patterns['reserved']['templates'])
                positive = random.choice(self.neutral_patterns['reserved']['positive'])
                superlative = random.choice(self.neutral_patterns['reserved']['superlative'])
                level = random.choice(self.neutral_patterns['reserved']['level'])
                text = template.format(positive=positive, superlative=superlative, level=level)

            else:  # expectation
                template = random.choice(self.neutral_patterns['expectation']['templates'])
                expectation = random.choice(self.neutral_patterns['expectation']['expectation'])
                text = template.format(expectation=expectation)

            samples.append(text)

        return samples

    def convert_to_neutral(self, text: str, sentiment: str) -> str:
        """
        将正面或负面评论转换为中评

        策略：
        - 正面评论 → 添加负面但书或弱化词
        - 负面评论 → 添加正面但书或弱化词

        Args:
            text: 原始文本
            sentiment: 'positive' 或 'negative'

        Returns:
            转换后的中评文本
        """
        if sentiment == 'positive':
            # 正面 → 中性：添加负面但书
            negative_clauses = [
                '，但价格有点贵',
                '，不过续航一般',
                '，就是有点小瑕疵',
                '，但没有想象中那么好',
                '，不过也就这样',
            ]
            return text + random.choice(negative_clauses)

        elif sentiment == 'negative':
            # 负面 → 中性：添加正面但书
            positive_clauses = [
                '，但外观还不错',
                '，不过价格便宜',
                '，但其他方面还行',
                '，不过也能接受',
                '，但总体还可以',
            ]
            return text + random.choice(positive_clauses)

        return text

    def augment_neutral_with_modifiers(self, text: str) -> List[str]:
        """
        通过添加弱化词来增强中评样本

        Args:
            text: 原始中评文本

        Returns:
            增强后的文本列表
        """
        words = list(jieba.cut(text))
        augmented = []

        # 在形容词前添加弱化词
        adjectives = ['好', '不错', '满意', '差', '烂', '棒', '赞']

        for i, word in enumerate(words):
            if word in adjectives:
                # 在形容词前插入弱化词
                modifier = random.choice(self.neutral_modifiers)
                new_words = words.copy()
                new_words.insert(i, modifier)
                augmented.append(''.join(new_words))

        return augmented if augmented else [text]


class NeutralBoundaryAnalyzer:
    """中评边界分析器 - 识别容易混淆的样本"""

    def __init__(self, confidence_threshold: float = 0.6):
        """
        Args:
            confidence_threshold: 置信度阈值，低于此值认为是边界样本
        """
        self.confidence_threshold = confidence_threshold

    def identify_boundary_samples(
        self,
        texts: List[str],
        labels: List[int],
        predictions: List[Tuple[int, float]]
    ) -> List[int]:
        """
        识别边界样本（容易混淆的样本）

        边界样本特征：
        1. 预测置信度低
        2. 预测错误
        3. 正负概率接近

        Args:
            texts: 文本列表
            labels: 真实标签
            predictions: 预测结果 [(predicted_label, confidence), ...]

        Returns:
            边界样本的索引列表
        """
        boundary_indices = []

        for i, (text, true_label, (pred_label, confidence)) in enumerate(
            zip(texts, labels, predictions)
        ):
            # 条件1：置信度低
            if confidence < self.confidence_threshold:
                boundary_indices.append(i)
                continue

            # 条件2：预测错误
            if pred_label != true_label:
                boundary_indices.append(i)

        return boundary_indices

    def suggest_relabeling(
        self,
        texts: List[str],
        labels: List[int],
        predictions: List[Tuple[int, float, dict]]
    ) -> List[Tuple[int, int, str]]:
        """
        建议重新标注的样本

        Args:
            texts: 文本列表
            labels: 真实标签 (0=negative, 1=neutral, 2=positive)
            predictions: 预测结果 [(pred_label, confidence, probabilities), ...]

        Returns:
            [(sample_idx, suggested_label, reason), ...]
        """
        suggestions = []

        for i, (text, true_label, (pred_label, confidence, probs)) in enumerate(
            zip(texts, labels, predictions)
        ):
            # 如果模型高置信度预测为中评，但标注为正/负
            if pred_label == 1 and true_label != 1 and confidence > 0.7:
                reason = f"模型高置信度({confidence:.2f})预测为中评，建议复核"
                suggestions.append((i, 1, reason))

            # 如果正负概率都较高（混合情感），建议标为中评
            if probs[0] > 0.3 and probs[2] > 0.3:  # negative和positive都>0.3
                reason = f"正负情感混合(neg={probs[0]:.2f}, pos={probs[2]:.2f})，建议标为中评"
                suggestions.append((i, 1, reason))

        return suggestions


def balance_neutral_samples(
    texts: List[str],
    labels: List[int],
    target_ratio: float = 0.33
) -> Tuple[List[str], List[int]]:
    """
    平衡中评样本数量

    通过合成样本使中评占比达到目标比例

    Args:
        texts: 原始文本列表
        labels: 原始标签列表 (0=negative, 1=neutral, 2=positive)
        target_ratio: 中评目标占比

    Returns:
        (平衡后的文本列表, 平衡后的标签列表)
    """
    from collections import Counter

    label_counts = Counter(labels)
    total = len(labels)
    neutral_count = label_counts[1]
    neutral_ratio = neutral_count / total

    print(f"当前中评占比: {neutral_ratio:.2%} ({neutral_count}/{total})")

    if neutral_ratio >= target_ratio:
        print("中评样本已充足，无需增强")
        return texts, labels

    # 计算需要增加的中评样本数
    target_neutral_count = int(total * target_ratio / (1 - target_ratio))
    needed = target_neutral_count - neutral_count

    print(f"需要增加 {needed} 个中评样本")

    # 生成合成样本
    enhancer = NeutralSampleEnhancer()
    synthetic_samples = enhancer.generate_synthetic_neutral(needed)

    # 合并数据
    balanced_texts = texts + synthetic_samples
    balanced_labels = labels + [1] * len(synthetic_samples)

    print(f"平衡后总样本数: {len(balanced_texts)}")
    print(f"平衡后中评占比: {len([l for l in balanced_labels if l == 1]) / len(balanced_labels):.2%}")

    return balanced_texts, balanced_labels
