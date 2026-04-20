"""
中评感知损失函数

针对中评判断不准确的问题，设计专门的损失函数和后处理策略。
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class NeutralAwareFocalLoss(nn.Module):
    """
    中评感知的Focal Loss

    核心思路：
    1. 对中评类别使用更高的权重
    2. 对正负边界样本（容易误判为中评的）增加惩罚
    3. 使用温度缩放调整决策边界

    Args:
        alpha: 类别权重 [negative, neutral, positive]，建议中评权重更高
        gamma: focal参数
        neutral_boost: 中评额外权重倍数（默认1.5倍）
        temperature: 温度参数，用于调整决策边界
    """

    def __init__(self, alpha=None, gamma=2.0, neutral_boost=1.5, temperature=1.0):
        super().__init__()
        self.gamma = gamma
        self.neutral_boost = neutral_boost
        self.temperature = temperature

        if alpha is not None:
            if isinstance(alpha, (list, tuple)):
                alpha = torch.tensor(alpha, dtype=torch.float32)
            # 对中评（索引1）应用额外权重
            alpha[1] *= neutral_boost
            self.alpha = alpha
        else:
            # 默认权重：中评权重更高
            self.alpha = torch.tensor([1.0, 1.5, 1.0], dtype=torch.float32)

    def forward(self, inputs, targets):
        """
        Args:
            inputs: (batch_size, 3) logits
            targets: (batch_size,) 标签 (0=negative, 1=neutral, 2=positive)
        """
        # 温度缩放
        inputs = inputs / self.temperature

        # 计算交叉熵
        ce_loss = F.cross_entropy(inputs, targets, reduction='none')

        # 计算预测概率
        p_t = torch.exp(-ce_loss)

        # Focal权重
        focal_weight = (1 - p_t) ** self.gamma

        # 类别权重
        if self.alpha.device != inputs.device:
            self.alpha = self.alpha.to(inputs.device)
        alpha_t = self.alpha[targets]

        # 最终损失
        loss = alpha_t * focal_weight * ce_loss

        return loss.mean()


class BoundaryAwareLoss(nn.Module):
    """
    边界感知损失

    核心思路：
    对于正负边界样本（容易混淆为中评的），增加额外的边界约束损失。

    边界样本定义：
    - 正面但不强烈（positive概率0.4-0.6）
    - 负面但不强烈（negative概率0.4-0.6）
    这些样本容易被误判为中评

    Args:
        base_criterion: 基础损失函数
        boundary_weight: 边界损失权重
        boundary_margin: 边界阈值 [lower, upper]
    """

    def __init__(self, base_criterion, boundary_weight=0.3,
                 boundary_margin=(0.4, 0.6)):
        super().__init__()
        self.base_criterion = base_criterion
        self.boundary_weight = boundary_weight
        self.boundary_margin = boundary_margin

    def forward(self, inputs, targets):
        """
        Args:
            inputs: (batch_size, 3) logits
            targets: (batch_size,) 标签
        """
        # 基础损失
        base_loss = self.base_criterion(inputs, targets)

        # 计算概率
        probs = F.softmax(inputs, dim=-1)

        # 识别边界样本
        # 正面边界：标签为positive(2)，但概率在边界范围内
        pos_boundary_mask = (
            (targets == 2) &
            (probs[:, 2] >= self.boundary_margin[0]) &
            (probs[:, 2] <= self.boundary_margin[1])
        )

        # 负面边界：标签为negative(0)，但概率在边界范围内
        neg_boundary_mask = (
            (targets == 0) &
            (probs[:, 0] >= self.boundary_margin[0]) &
            (probs[:, 0] <= self.boundary_margin[1])
        )

        boundary_mask = pos_boundary_mask | neg_boundary_mask

        # 边界损失：鼓励边界样本的预测更加确定
        if boundary_mask.any():
            # 对边界样本，增加熵惩罚（鼓励更确定的预测）
            entropy = -(probs * torch.log(probs + 1e-8)).sum(dim=-1)
            boundary_loss = entropy[boundary_mask].mean()

            total_loss = base_loss + self.boundary_weight * boundary_loss
        else:
            total_loss = base_loss

        return total_loss


class ConfusionMatrixLoss(nn.Module):
    """
    混淆矩阵感知损失

    根据混淆矩阵动态调整损失权重，重点优化容易混淆的类别对。

    例如：如果发现"正面→中评"的误判很多，就增加这个方向的惩罚。

    Args:
        base_criterion: 基础损失函数
        confusion_weights: 混淆权重矩阵 (3x3)
            confusion_weights[i][j] 表示真实类别i被预测为j的额外惩罚权重
    """

    def __init__(self, base_criterion, confusion_weights=None):
        super().__init__()
        self.base_criterion = base_criterion

        if confusion_weights is None:
            # 默认权重：重点惩罚"正/负→中评"的误判
            confusion_weights = torch.tensor([
                [1.0, 1.5, 1.0],  # negative → neutral 惩罚1.5倍
                [1.5, 1.0, 1.5],  # neutral → pos/neg 惩罚1.5倍
                [1.0, 1.5, 1.0],  # positive → neutral 惩罚1.5倍
            ], dtype=torch.float32)

        self.confusion_weights = confusion_weights

    def forward(self, inputs, targets):
        """
        Args:
            inputs: (batch_size, 3) logits
            targets: (batch_size,) 标签
        """
        # 基础损失（不进行reduction）
        if hasattr(self.base_criterion, 'reduction'):
            original_reduction = self.base_criterion.reduction
            self.base_criterion.reduction = 'none'
            base_loss = self.base_criterion(inputs, targets)
            self.base_criterion.reduction = original_reduction
        else:
            ce_loss = F.cross_entropy(inputs, targets, reduction='none')
            base_loss = ce_loss

        # 获取预测类别
        preds = torch.argmax(inputs, dim=-1)

        # 应用混淆权重
        if self.confusion_weights.device != inputs.device:
            self.confusion_weights = self.confusion_weights.to(inputs.device)

        # 为每个样本获取对应的混淆权重
        weights = self.confusion_weights[targets, preds]

        # 加权损失
        weighted_loss = base_loss * weights

        return weighted_loss.mean()


class OrdinalRegressionLoss(nn.Module):
    """
    序数回归损失

    将情感分类视为序数回归问题：negative < neutral < positive

    核心思路：
    - 预测为positive但实际是negative，比预测为neutral惩罚更重
    - 利用类别之间的顺序关系

    Args:
        margin: 序数间隔
    """

    def __init__(self, margin=1.0):
        super().__init__()
        self.margin = margin

    def forward(self, inputs, targets):
        """
        Args:
            inputs: (batch_size, 3) logits
            targets: (batch_size,) 标签 (0, 1, 2)
        """
        batch_size = inputs.size(0)

        # 转换为序数值：0→-1, 1→0, 2→1
        ordinal_targets = targets.float() - 1.0

        # 使用中间类别的logit作为预测值
        # 或者使用加权和：-1*p(neg) + 0*p(neu) + 1*p(pos)
        probs = F.softmax(inputs, dim=-1)
        ordinal_preds = -1.0 * probs[:, 0] + 0.0 * probs[:, 1] + 1.0 * probs[:, 2]

        # 计算序数距离
        ordinal_distance = torch.abs(ordinal_preds - ordinal_targets)

        # 使用平滑L1损失
        loss = F.smooth_l1_loss(ordinal_preds, ordinal_targets, reduction='mean')

        return loss


def create_neutral_aware_criterion(
    loss_type='neutral_focal',
    class_weights=None,
    **kwargs
):
    """
    创建中评感知的损失函数

    Args:
        loss_type: 损失类型
            - 'neutral_focal': 中评感知Focal Loss
            - 'boundary_aware': 边界感知损失
            - 'confusion_aware': 混淆矩阵感知损失
            - 'ordinal': 序数回归损失
        class_weights: 类别权重
        **kwargs: 其他参数

    Returns:
        损失函数
    """
    if loss_type == 'neutral_focal':
        return NeutralAwareFocalLoss(
            alpha=class_weights,
            gamma=kwargs.get('gamma', 2.0),
            neutral_boost=kwargs.get('neutral_boost', 1.5),
            temperature=kwargs.get('temperature', 1.0)
        )

    elif loss_type == 'boundary_aware':
        base_criterion = nn.CrossEntropyLoss()
        return BoundaryAwareLoss(
            base_criterion=base_criterion,
            boundary_weight=kwargs.get('boundary_weight', 0.3),
            boundary_margin=kwargs.get('boundary_margin', (0.4, 0.6))
        )

    elif loss_type == 'confusion_aware':
        base_criterion = nn.CrossEntropyLoss()
        return ConfusionMatrixLoss(
            base_criterion=base_criterion,
            confusion_weights=kwargs.get('confusion_weights', None)
        )

    elif loss_type == 'ordinal':
        return OrdinalRegressionLoss(
            margin=kwargs.get('margin', 1.0)
        )

    else:
        raise ValueError(f"未知的损失类型: {loss_type}")
