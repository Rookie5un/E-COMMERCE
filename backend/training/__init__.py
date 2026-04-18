"""
训练工具包

包含模型训练相关的优化模块：
- losses: 自定义损失函数（Focal Loss, Label Smoothing等）
- augmentation: 数据增强策略
- pooling: 自定义池化层
- cross_validation: K折交叉验证
- ensemble: 模型集成
- inference_optimizer: 推理优化
"""

__version__ = '1.0.0'

from .losses import FocalLoss, LabelSmoothingCrossEntropy
from .augmentation import TextAugmenter

__all__ = [
    'FocalLoss',
    'LabelSmoothingCrossEntropy',
    'TextAugmenter',
]
