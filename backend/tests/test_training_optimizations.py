"""
训练优化模块单元测试
"""

import unittest
import torch
import numpy as np
from training.losses import FocalLoss, LabelSmoothingCrossEntropy
from training.augmentation import TextAugmenter
from training.pooling import AttentionPooling, MeanPooling, MaxPooling


class TestFocalLoss(unittest.TestCase):
    """测试 Focal Loss"""

    def test_focal_loss_basic(self):
        """测试基本功能"""
        criterion = FocalLoss(gamma=2.0)
        logits = torch.randn(32, 3)
        targets = torch.randint(0, 3, (32,))
        loss = criterion(logits, targets)

        self.assertIsInstance(loss.item(), float)
        self.assertGreater(loss.item(), 0)

    def test_focal_loss_with_alpha(self):
        """测试类别权重"""
        alpha = [0.25, 0.25, 0.5]
        criterion = FocalLoss(alpha=alpha, gamma=2.0)
        logits = torch.randn(32, 3)
        targets = torch.randint(0, 3, (32,))
        loss = criterion(logits, targets)

        self.assertIsInstance(loss.item(), float)
        self.assertGreater(loss.item(), 0)

    def test_focal_loss_gamma_zero(self):
        """测试 gamma=0 时等价于交叉熵"""
        criterion_focal = FocalLoss(gamma=0.0)
        criterion_ce = torch.nn.CrossEntropyLoss()

        logits = torch.randn(32, 3)
        targets = torch.randint(0, 3, (32,))

        loss_focal = criterion_focal(logits, targets)
        loss_ce = criterion_ce(logits, targets)

        # 应该非常接近
        self.assertAlmostEqual(loss_focal.item(), loss_ce.item(), places=5)


class TestLabelSmoothingCrossEntropy(unittest.TestCase):
    """测试标签平滑交叉熵"""

    def test_label_smoothing_basic(self):
        """测试基本功能"""
        criterion = LabelSmoothingCrossEntropy(smoothing=0.1)
        logits = torch.randn(32, 3)
        targets = torch.randint(0, 3, (32,))
        loss = criterion(logits, targets)

        self.assertIsInstance(loss.item(), float)
        self.assertGreater(loss.item(), 0)

    def test_label_smoothing_zero(self):
        """测试 smoothing=0 时等价于交叉熵"""
        criterion_ls = LabelSmoothingCrossEntropy(smoothing=0.0)
        criterion_ce = torch.nn.CrossEntropyLoss()

        logits = torch.randn(32, 3)
        targets = torch.randint(0, 3, (32,))

        loss_ls = criterion_ls(logits, targets)
        loss_ce = criterion_ce(logits, targets)

        # 应该非常接近
        self.assertAlmostEqual(loss_ls.item(), loss_ce.item(), places=5)


class TestTextAugmenter(unittest.TestCase):
    """测试文本数据增强"""

    def setUp(self):
        self.augmenter = TextAugmenter()

    def test_augment_basic(self):
        """测试基本增强"""
        text = "这个手机很好用，推荐购买"
        augmented = self.augmenter.augment(text, num_aug=2)

        self.assertEqual(len(augmented), 2)
        for aug_text in augmented:
            self.assertIsInstance(aug_text, str)
            self.assertGreater(len(aug_text), 0)

    def test_synonym_replacement(self):
        """测试同义词替换"""
        text = "这个手机很好用"
        words = list(text)
        result = self.augmenter._synonym_replacement(words, n=1)

        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)

    def test_random_insertion(self):
        """测试随机插入"""
        text = "这个手机很好用"
        words = list(text)
        result = self.augmenter._random_insertion(words, n=1)

        self.assertIsInstance(result, list)
        # 插入后长度应该增加
        self.assertGreaterEqual(len(result), len(words))

    def test_random_swap(self):
        """测试随机交换"""
        text = "这个手机很好用"
        words = list(text)
        result = self.augmenter._random_swap(words, n=1)

        self.assertIsInstance(result, list)
        # 交换后长度不变
        self.assertEqual(len(result), len(words))

    def test_random_deletion(self):
        """测试随机删除"""
        text = "这个手机很好用"
        words = list(text)
        result = self.augmenter._random_deletion(words, p=0.2)

        self.assertIsInstance(result, list)
        # 至少保留一个词
        self.assertGreater(len(result), 0)

    def test_empty_text(self):
        """测试空文本"""
        text = ""
        augmented = self.augmenter.augment(text, num_aug=1)

        self.assertEqual(len(augmented), 1)
        self.assertEqual(augmented[0], "")


class TestPoolingLayers(unittest.TestCase):
    """测试池化层"""

    def test_attention_pooling(self):
        """测试注意力池化"""
        pooling = AttentionPooling(hidden_size=768)
        hidden_states = torch.randn(32, 128, 768)
        attention_mask = torch.ones(32, 128)

        pooled = pooling(hidden_states, attention_mask)

        self.assertEqual(pooled.shape, (32, 768))

    def test_attention_pooling_with_mask(self):
        """测试带mask的注意力池化"""
        pooling = AttentionPooling(hidden_size=768)
        hidden_states = torch.randn(32, 128, 768)
        attention_mask = torch.ones(32, 128)
        # 将后半部分设为padding
        attention_mask[:, 64:] = 0

        pooled = pooling(hidden_states, attention_mask)

        self.assertEqual(pooled.shape, (32, 768))

    def test_mean_pooling(self):
        """测试平均池化"""
        pooling = MeanPooling()
        hidden_states = torch.randn(32, 128, 768)
        attention_mask = torch.ones(32, 128)

        pooled = pooling(hidden_states, attention_mask)

        self.assertEqual(pooled.shape, (32, 768))

    def test_max_pooling(self):
        """测试最大池化"""
        pooling = MaxPooling()
        hidden_states = torch.randn(32, 128, 768)
        attention_mask = torch.ones(32, 128)

        pooled = pooling(hidden_states, attention_mask)

        self.assertEqual(pooled.shape, (32, 768))


class TestIntegration(unittest.TestCase):
    """集成测试"""

    def test_focal_loss_backward(self):
        """测试 Focal Loss 反向传播"""
        criterion = FocalLoss(gamma=2.0)
        logits = torch.randn(32, 3, requires_grad=True)
        targets = torch.randint(0, 3, (32,))

        loss = criterion(logits, targets)
        loss.backward()

        # 检查梯度是否计算
        self.assertIsNotNone(logits.grad)
        self.assertEqual(logits.grad.shape, logits.shape)

    def test_augmenter_preserves_sentiment(self):
        """测试增强后情感倾向保持"""
        augmenter = TextAugmenter()

        # 正向文本
        positive_text = "这个手机非常好用，强烈推荐"
        augmented = augmenter.augment(positive_text, num_aug=5)

        # 检查增强后的文本仍包含正向词汇
        for aug_text in augmented:
            # 至少应该包含一些正向相关的词
            self.assertTrue(
                any(word in aug_text for word in ['好', '不错', '推荐', '棒', '赞'])
            )


if __name__ == '__main__':
    unittest.main()
