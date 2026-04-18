"""
自定义损失函数模块

包含用于处理类别不平衡和提升模型泛化能力的损失函数：
- FocalLoss: 聚焦于难分类样本，缓解类别不平衡
- LabelSmoothingCrossEntropy: 标签平滑，防止过拟合
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class FocalLoss(nn.Module):
    """
    Focal Loss for addressing class imbalance

    论文: Focal Loss for Dense Object Detection (https://arxiv.org/abs/1708.02002)

    公式: FL(p_t) = -α_t * (1 - p_t)^γ * log(p_t)

    其中:
    - p_t: 正确类别的预测概率
    - α_t: 类别权重，用于平衡正负样本
    - γ: 聚焦参数，控制难易样本的权重差异

    当 γ=0 时，Focal Loss 退化为标准交叉熵损失。
    当 γ>0 时，易分类样本的损失被降低，模型更关注难分类样本。

    Args:
        alpha: 类别权重，可以是：
            - None: 不使用类别权重
            - list/tuple: 每个类别的权重 [w0, w1, w2]
            - torch.Tensor: 权重张量
        gamma: 聚焦参数，默认2.0
            - γ=0: 等价于交叉熵
            - γ=1: 轻度聚焦
            - γ=2: 标准聚焦（推荐）
            - γ=5: 强聚焦
        reduction: 'mean', 'sum' 或 'none'

    Example:
        >>> criterion = FocalLoss(alpha=[0.25, 0.25, 0.5], gamma=2.0)
        >>> logits = torch.randn(32, 3)  # batch_size=32, num_classes=3
        >>> targets = torch.randint(0, 3, (32,))
        >>> loss = criterion(logits, targets)
    """

    def __init__(self, alpha=None, gamma=2.0, reduction='mean'):
        super().__init__()
        self.gamma = gamma
        self.reduction = reduction

        # 处理 alpha 参数
        if alpha is not None:
            if isinstance(alpha, (list, tuple)):
                self.alpha = torch.tensor(alpha, dtype=torch.float32)
            else:
                self.alpha = alpha
        else:
            self.alpha = None

    def forward(self, inputs, targets):
        """
        Args:
            inputs: (batch_size, num_classes) 模型输出的 logits
            targets: (batch_size,) 真实类别索引

        Returns:
            loss: 标量损失值
        """
        # 计算交叉熵损失（不进行reduction）
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')

        # 计算预测概率 p_t
        p_t = torch.exp(-ce_loss)

        # 计算 Focal Loss: (1 - p_t)^γ * CE
        focal_loss = (1 - p_t) ** self.gamma * ce_loss

        # 应用类别权重 α_t
        if self.alpha is not None:
            if self.alpha.device != inputs.device:
                self.alpha = self.alpha.to(inputs.device)

            # 获取每个样本对应类别的权重
            alpha_t = self.alpha[targets]
            focal_loss = alpha_t * focal_loss

        # 应用 reduction
        if self.reduction == 'mean':
            return focal_loss.mean()
        elif self.reduction == 'sum':
            return focal_loss.sum()
        else:
            return focal_loss


class LabelSmoothingCrossEntropy(nn.Module):
    """
    标签平滑交叉熵损失

    标签平滑通过将硬标签 [0, 0, 1] 软化为 [ε/K, ε/K, 1-ε+ε/K] 来防止过拟合，
    其中 ε 是平滑系数，K 是类别数。

    优点:
    1. 防止模型对预测过于自信
    2. 提升模型泛化能力
    3. 缓解标注噪声的影响

    Args:
        smoothing: 平滑系数 ε，范围 [0, 1)
            - 0.0: 无平滑，等价于标准交叉熵
            - 0.1: 轻度平滑（推荐）
            - 0.2: 中度平滑
            - 0.3+: 强平滑（可能影响性能）
        reduction: 'mean', 'sum' 或 'none'

    Example:
        >>> criterion = LabelSmoothingCrossEntropy(smoothing=0.1)
        >>> logits = torch.randn(32, 3)
        >>> targets = torch.randint(0, 3, (32,))
        >>> loss = criterion(logits, targets)
    """

    def __init__(self, smoothing=0.1, reduction='mean'):
        super().__init__()
        assert 0.0 <= smoothing < 1.0, "smoothing 必须在 [0, 1) 范围内"
        self.smoothing = smoothing
        self.reduction = reduction

    def forward(self, inputs, targets):
        """
        Args:
            inputs: (batch_size, num_classes) 模型输出的 logits
            targets: (batch_size,) 真实类别索引

        Returns:
            loss: 标量损失值
        """
        num_classes = inputs.size(-1)

        # 计算 log softmax
        log_probs = F.log_softmax(inputs, dim=-1)

        # 计算标准负对数似然损失（针对真实类别）
        nll_loss = -log_probs.gather(dim=-1, index=targets.unsqueeze(1))
        nll_loss = nll_loss.squeeze(1)

        # 计算平滑损失（所有类别的平均负对数似然）
        smooth_loss = -log_probs.mean(dim=-1)

        # 组合损失: (1-ε) * NLL + ε * smooth
        loss = (1 - self.smoothing) * nll_loss + self.smoothing * smooth_loss

        # 应用 reduction
        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss


class WeightedFocalLoss(nn.Module):
    """
    加权 Focal Loss（结合类别权重和样本权重）

    适用于同时存在类别不平衡和样本重要性差异的场景。

    Args:
        alpha: 类别权重
        gamma: 聚焦参数
        sample_weights: 样本权重 (batch_size,)，可选
        reduction: 'mean', 'sum' 或 'none'
    """

    def __init__(self, alpha=None, gamma=2.0, reduction='mean'):
        super().__init__()
        self.focal_loss = FocalLoss(alpha=alpha, gamma=gamma, reduction='none')
        self.reduction = reduction

    def forward(self, inputs, targets, sample_weights=None):
        """
        Args:
            inputs: (batch_size, num_classes) logits
            targets: (batch_size,) 类别索引
            sample_weights: (batch_size,) 样本权重，可选
        """
        loss = self.focal_loss(inputs, targets)

        if sample_weights is not None:
            loss = loss * sample_weights

        if self.reduction == 'mean':
            return loss.mean()
        elif self.reduction == 'sum':
            return loss.sum()
        else:
            return loss


# 便捷函数
def focal_loss(inputs, targets, alpha=None, gamma=2.0, reduction='mean'):
    """
    Focal Loss 函数式接口

    Args:
        inputs: (batch_size, num_classes) logits
        targets: (batch_size,) 类别索引
        alpha: 类别权重
        gamma: 聚焦参数
        reduction: 'mean', 'sum' 或 'none'

    Returns:
        loss: 损失值
    """
    criterion = FocalLoss(alpha=alpha, gamma=gamma, reduction=reduction)
    return criterion(inputs, targets)


def label_smoothing_cross_entropy(inputs, targets, smoothing=0.1, reduction='mean'):
    """
    标签平滑交叉熵函数式接口

    Args:
        inputs: (batch_size, num_classes) logits
        targets: (batch_size,) 类别索引
        smoothing: 平滑系数
        reduction: 'mean', 'sum' 或 'none'

    Returns:
        loss: 损失值
    """
    criterion = LabelSmoothingCrossEntropy(smoothing=smoothing, reduction=reduction)
    return criterion(inputs, targets)
