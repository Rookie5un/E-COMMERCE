"""
文本数据增强模块

实现 EDA (Easy Data Augmentation) 增强版，包括：
- 同义词替换 (Synonym Replacement, SR)
- 随机插入 (Random Insertion, RI)
- 随机交换 (Random Swap, RS)
- 随机删除 (Random Deletion, RD)

参考论文: EDA: Easy Data Augmentation Techniques for Boosting Performance on Text Classification Tasks
"""

import random
import jieba
from typing import List, Dict, Optional


class TextAugmenter:
    """
    文本数据增强器

    支持多种数据增强策略，提升模型泛化能力。

    Args:
        synonym_dict: 同义词词典，格式 {'词': ['同义词1', '同义词2', ...]}
        stopwords: 停用词集合，增强时会跳过停用词

    Example:
        >>> augmenter = TextAugmenter()
        >>> text = "这个手机很好用，推荐购买"
        >>> augmented = augmenter.augment(text, num_aug=2)
        >>> print(augmented)
        ['这个手机很不错，推荐购买', '这个手机很好用，强烈推荐购买']
    """

    def __init__(self, synonym_dict: Optional[Dict[str, List[str]]] = None,
                 stopwords: Optional[set] = None):
        self.synonym_dict = synonym_dict or self._default_synonym_dict()
        self.stopwords = stopwords or self._default_stopwords()

    def _default_synonym_dict(self) -> Dict[str, List[str]]:
        """
        默认同义词词典（电商评论领域）

        注意：仅包含情感极性一致的同义词，避免改变情感倾向
        """
        return {
            # 正向词汇
            '好': ['不错', '优秀', '棒', '赞', '给力'],
            '满意': ['喜欢', '中意', '满足'],
            '推荐': ['安利', '种草', '强烈推荐'],
            '快': ['迅速', '神速', '飞快', '快速'],
            '清晰': ['清楚', '高清', '明亮'],
            '流畅': ['顺畅', '丝滑', '不卡'],
            '漂亮': ['好看', '美观', '精致'],
            '实惠': ['划算', '便宜', '性价比高'],
            '质量好': ['品质好', '做工好', '质量不错'],

            # 负向词汇
            '差': ['烂', '糟糕', '不好', '劣质'],
            '失望': ['遗憾', '不满', '后悔'],
            '慢': ['缓慢', '磨蹭', '拖沓'],
            '卡顿': ['卡', '不流畅', '掉帧'],
            '发热': ['烫', '发烫', '温度高'],
            '贵': ['昂贵', '不值', '太贵'],
            '假': ['仿品', '山寨', '假货'],
            '坏': ['损坏', '破损', '有问题'],

            # 中性词汇
            '使用': ['用', '试用', '体验'],
            '购买': ['买', '入手', '下单'],
            '收到': ['拿到', '到货', '送达'],
            '包装': ['外包装', '盒子', '快递包装'],
        }

    def _default_stopwords(self) -> set:
        """默认停用词（增强时跳过）"""
        return {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
        }

    def augment(self, text: str, num_aug: int = 1,
                alpha_sr: float = 0.1, alpha_ri: float = 0.1,
                alpha_rs: float = 0.1, alpha_rd: float = 0.1) -> List[str]:
        """
        数据增强主函数

        Args:
            text: 原始文本
            num_aug: 生成增强样本数量
            alpha_sr: 同义词替换比例（替换词数 = len(words) * alpha_sr）
            alpha_ri: 随机插入比例
            alpha_rs: 随机交换比例
            alpha_rd: 随机删除概率

        Returns:
            增强后的文本列表
        """
        if not text or not text.strip():
            return [text] * num_aug

        words = list(jieba.cut(text))
        if len(words) == 0:
            return [text] * num_aug

        augmented_texts = []

        for _ in range(num_aug):
            aug_words = words.copy()

            # 随机选择增强策略（可以组合多种策略）
            strategies = []
            if random.random() < 0.8:  # 80% 概率应用同义词替换
                strategies.append('sr')
            if random.random() < 0.3:  # 30% 概率应用随机插入
                strategies.append('ri')
            if random.random() < 0.3:  # 30% 概率应用随机交换
                strategies.append('rs')
            if random.random() < 0.2:  # 20% 概率应用随机删除
                strategies.append('rd')

            # 应用增强策略
            for strategy in strategies:
                if strategy == 'sr':
                    n = max(1, int(len(words) * alpha_sr))
                    aug_words = self._synonym_replacement(aug_words, n)
                elif strategy == 'ri':
                    n = max(1, int(len(words) * alpha_ri))
                    aug_words = self._random_insertion(aug_words, n)
                elif strategy == 'rs':
                    n = max(1, int(len(words) * alpha_rs))
                    aug_words = self._random_swap(aug_words, n)
                elif strategy == 'rd':
                    aug_words = self._random_deletion(aug_words, alpha_rd)

            augmented_text = ''.join(aug_words)
            augmented_texts.append(augmented_text if augmented_text else text)

        return augmented_texts

    def _synonym_replacement(self, words: List[str], n: int) -> List[str]:
        """
        同义词替换

        随机选择 n 个词，替换为其同义词

        Args:
            words: 分词列表
            n: 替换词数

        Returns:
            替换后的分词列表
        """
        new_words = words.copy()

        # 找出可以替换的词（在同义词词典中且不是停用词）
        replaceable_words = [
            (i, word) for i, word in enumerate(words)
            if word in self.synonym_dict and word not in self.stopwords
        ]

        if not replaceable_words:
            return new_words

        # 随机选择要替换的词
        random.shuffle(replaceable_words)
        num_replaced = 0

        for idx, word in replaceable_words:
            if num_replaced >= n:
                break

            # 随机选择一个同义词
            synonyms = self.synonym_dict[word]
            synonym = random.choice(synonyms)
            new_words[idx] = synonym
            num_replaced += 1

        return new_words

    def _random_insertion(self, words: List[str], n: int) -> List[str]:
        """
        随机插入

        随机插入 n 个同义词到句子中

        Args:
            words: 分词列表
            n: 插入词数

        Returns:
            插入后的分词列表
        """
        new_words = words.copy()

        for _ in range(n):
            self._add_word(new_words)

        return new_words

    def _add_word(self, words: List[str]):
        """
        插入一个随机同义词

        从句子中随机选择一个词，找到其同义词，插入到随机位置
        """
        # 找出有同义词的词
        synonym_words = [
            word for word in words
            if word in self.synonym_dict and word not in self.stopwords
        ]

        if not synonym_words:
            return

        # 随机选择一个词
        random_word = random.choice(synonym_words)
        synonyms = self.synonym_dict[random_word]
        random_synonym = random.choice(synonyms)

        # 插入到随机位置
        random_idx = random.randint(0, len(words))
        words.insert(random_idx, random_synonym)

    def _random_swap(self, words: List[str], n: int) -> List[str]:
        """
        随机交换

        随机交换 n 对词的位置

        Args:
            words: 分词列表
            n: 交换次数

        Returns:
            交换后的分词列表
        """
        new_words = words.copy()
        length = len(new_words)

        if length < 2:
            return new_words

        for _ in range(n):
            # 随机选择两个不同的位置
            idx1, idx2 = random.sample(range(length), 2)
            new_words[idx1], new_words[idx2] = new_words[idx2], new_words[idx1]

        return new_words

    def _random_deletion(self, words: List[str], p: float) -> List[str]:
        """
        随机删除

        以概率 p 删除每个词

        Args:
            words: 分词列表
            p: 删除概率

        Returns:
            删除后的分词列表
        """
        # 如果只有一个词，不删除
        if len(words) == 1:
            return words

        new_words = []
        for word in words:
            # 以概率 (1-p) 保留词
            if random.random() > p:
                new_words.append(word)

        # 至少保留一个词
        if len(new_words) == 0:
            return [random.choice(words)]

        return new_words

    def add_synonyms(self, word: str, synonyms: List[str]):
        """
        添加自定义同义词

        Args:
            word: 原词
            synonyms: 同义词列表
        """
        self.synonym_dict[word] = synonyms

    def remove_synonyms(self, word: str):
        """移除同义词"""
        if word in self.synonym_dict:
            del self.synonym_dict[word]


# 便捷函数
def augment_text(text: str, num_aug: int = 1, **kwargs) -> List[str]:
    """
    文本增强便捷函数

    Args:
        text: 原始文本
        num_aug: 增强样本数量
        **kwargs: 传递给 TextAugmenter.augment() 的参数

    Returns:
        增强后的文本列表
    """
    augmenter = TextAugmenter()
    return augmenter.augment(text, num_aug=num_aug, **kwargs)
