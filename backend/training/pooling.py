"""
自定义池化层

提供替代[CLS]标记的池化策略，更好地聚合序列信息。
"""

import torch
import torch.nn as nn


class AttentionPooling(nn.Module):
    """
    注意力池化层

    使用可学习的注意力机制对序列中的所有token进行加权平均，
    相比直接使用[CLS]标记，能够更好地捕获整个序列的信息。

    原理:
    1. 对每个token计算注意力分数
    2. 使用softmax归一化得到注意力权重
    3. 对所有token进行加权求和

    Args:
        hidden_size: 隐藏层维度

    Example:
        >>> pooling = AttentionPooling(hidden_size=768)
        >>> hidden_states = torch.randn(32, 128, 768)  # (batch, seq_len, hidden)
        >>> attention_mask = torch.ones(32, 128)
        >>> pooled = pooling(hidden_states, attention_mask)
        >>> print(pooled.shape)  # (32, 768)
    """

    def __init__(self, hidden_size: int):
        super().__init__()
        self.attention = nn.Linear(hidden_size, 1)

    def forward(self, hidden_states: torch.Tensor, attention_mask: torch.Tensor = None) -> torch.Tensor:
        """
        Args:
            hidden_states: (batch_size, seq_len, hidden_size) BERT输出的隐藏状态
            attention_mask: (batch_size, seq_len) 注意力掩码，1表示有效token，0表示padding

        Returns:
            pooled_output: (batch_size, hidden_size) 池化后的输出
        """
        # 计算注意力分数: (batch, seq_len, hidden) -> (batch, seq_len, 1) -> (batch, seq_len)
        attention_scores = self.attention(hidden_states).squeeze(-1)

        # 应用mask：将padding位置的分数设为负无穷
        if attention_mask is not None:
            attention_scores = attention_scores.masked_fill(
                attention_mask == 0,
                float('-inf')
            )

        # Softmax归一化得到注意力权重: (batch, seq_len)
        attention_weights = torch.softmax(attention_scores, dim=-1)

        # 加权求和: (batch, 1, seq_len) @ (batch, seq_len, hidden) -> (batch, 1, hidden) -> (batch, hidden)
        pooled_output = torch.bmm(
            attention_weights.unsqueeze(1),
            hidden_states
        ).squeeze(1)

        return pooled_output


class MultiHeadAttentionPooling(nn.Module):
    """
    多头注意力池化层

    使用多个注意力头从不同角度聚合序列信息。

    Args:
        hidden_size: 隐藏层维度
        num_heads: 注意力头数量

    Example:
        >>> pooling = MultiHeadAttentionPooling(hidden_size=768, num_heads=8)
        >>> hidden_states = torch.randn(32, 128, 768)
        >>> pooled = pooling(hidden_states)
        >>> print(pooled.shape)  # (32, 768)
    """

    def __init__(self, hidden_size: int, num_heads: int = 8):
        super().__init__()
        assert hidden_size % num_heads == 0, "hidden_size 必须能被 num_heads 整除"

        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads

        self.query = nn.Linear(hidden_size, hidden_size)
        self.key = nn.Linear(hidden_size, hidden_size)
        self.value = nn.Linear(hidden_size, hidden_size)
        self.output = nn.Linear(hidden_size, hidden_size)

    def forward(self, hidden_states: torch.Tensor, attention_mask: torch.Tensor = None) -> torch.Tensor:
        """
        Args:
            hidden_states: (batch_size, seq_len, hidden_size)
            attention_mask: (batch_size, seq_len)

        Returns:
            pooled_output: (batch_size, hidden_size)
        """
        batch_size, seq_len, _ = hidden_states.size()

        # 使用序列的平均值作为query
        if attention_mask is not None:
            mask_expanded = attention_mask.unsqueeze(-1).expand_as(hidden_states)
            sum_hidden = (hidden_states * mask_expanded).sum(dim=1)
            sum_mask = mask_expanded.sum(dim=1)
            query_vector = sum_hidden / sum_mask.clamp(min=1e-9)
        else:
            query_vector = hidden_states.mean(dim=1)

        # 线性变换
        Q = self.query(query_vector)  # (batch, hidden)
        K = self.key(hidden_states)   # (batch, seq_len, hidden)
        V = self.value(hidden_states) # (batch, seq_len, hidden)

        # 重塑为多头: (batch, num_heads, head_dim)
        Q = Q.view(batch_size, self.num_heads, self.head_dim)
        K = K.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)

        # 计算注意力分数: (batch, num_heads, 1, seq_len)
        scores = torch.matmul(Q.unsqueeze(2), K.transpose(-2, -1)) / (self.head_dim ** 0.5)

        # 应用mask
        if attention_mask is not None:
            mask_expanded = attention_mask.unsqueeze(1).unsqueeze(2)  # (batch, 1, 1, seq_len)
            scores = scores.masked_fill(mask_expanded == 0, float('-inf'))

        # Softmax
        attention_weights = torch.softmax(scores, dim=-1)

        # 加权求和: (batch, num_heads, 1, seq_len) @ (batch, num_heads, seq_len, head_dim)
        # -> (batch, num_heads, 1, head_dim)
        context = torch.matmul(attention_weights, V).squeeze(2)

        # 合并多头: (batch, num_heads, head_dim) -> (batch, hidden)
        context = context.contiguous().view(batch_size, self.hidden_size)

        # 输出变换
        pooled_output = self.output(context)

        return pooled_output


class MeanPooling(nn.Module):
    """
    平均池化层

    对序列中的所有有效token进行平均（忽略padding）。

    Example:
        >>> pooling = MeanPooling()
        >>> hidden_states = torch.randn(32, 128, 768)
        >>> attention_mask = torch.ones(32, 128)
        >>> pooled = pooling(hidden_states, attention_mask)
        >>> print(pooled.shape)  # (32, 768)
    """

    def forward(self, hidden_states: torch.Tensor, attention_mask: torch.Tensor = None) -> torch.Tensor:
        """
        Args:
            hidden_states: (batch_size, seq_len, hidden_size)
            attention_mask: (batch_size, seq_len)

        Returns:
            pooled_output: (batch_size, hidden_size)
        """
        if attention_mask is None:
            return hidden_states.mean(dim=1)

        # 扩展mask维度: (batch, seq_len) -> (batch, seq_len, hidden)
        mask_expanded = attention_mask.unsqueeze(-1).expand_as(hidden_states)

        # 对有效token求和
        sum_hidden = (hidden_states * mask_expanded).sum(dim=1)

        # 计算有效token数量
        sum_mask = mask_expanded.sum(dim=1).clamp(min=1e-9)

        # 平均
        pooled_output = sum_hidden / sum_mask

        return pooled_output


class MaxPooling(nn.Module):
    """
    最大池化层

    对序列中的所有有效token取最大值（忽略padding）。

    Example:
        >>> pooling = MaxPooling()
        >>> hidden_states = torch.randn(32, 128, 768)
        >>> attention_mask = torch.ones(32, 128)
        >>> pooled = pooling(hidden_states, attention_mask)
        >>> print(pooled.shape)  # (32, 768)
    """

    def forward(self, hidden_states: torch.Tensor, attention_mask: torch.Tensor = None) -> torch.Tensor:
        """
        Args:
            hidden_states: (batch_size, seq_len, hidden_size)
            attention_mask: (batch_size, seq_len)

        Returns:
            pooled_output: (batch_size, hidden_size)
        """
        if attention_mask is None:
            return hidden_states.max(dim=1)[0]

        # 将padding位置设为负无穷
        mask_expanded = attention_mask.unsqueeze(-1).expand_as(hidden_states)
        hidden_states = hidden_states.clone()
        hidden_states[mask_expanded == 0] = float('-inf')

        # 取最大值
        pooled_output = hidden_states.max(dim=1)[0]

        return pooled_output


class RoBERTaWithCustomPooling(nn.Module):
    """
    带自定义池化的RoBERTa模型

    替换标准的[CLS]池化为自定义池化策略。

    Args:
        base_model: 预训练的BERT/RoBERTa模型
        num_labels: 分类类别数
        pooling_type: 池化类型，'attention', 'mean', 'max', 'multihead'
        dropout_prob: Dropout概率

    Example:
        >>> from transformers import BertForSequenceClassification
        >>> base_model = BertForSequenceClassification.from_pretrained('bert-base-chinese')
        >>> model = RoBERTaWithCustomPooling(base_model, num_labels=3, pooling_type='attention')
    """

    def __init__(self, base_model, num_labels: int = 3,
                 pooling_type: str = 'attention', dropout_prob: float = 0.1):
        super().__init__()

        self.bert = base_model.bert if hasattr(base_model, 'bert') else base_model.roberta
        self.config = base_model.config
        self.num_labels = num_labels

        # 选择池化层
        hidden_size = self.config.hidden_size
        if pooling_type == 'attention':
            self.pooling = AttentionPooling(hidden_size)
        elif pooling_type == 'multihead':
            self.pooling = MultiHeadAttentionPooling(hidden_size, num_heads=8)
        elif pooling_type == 'mean':
            self.pooling = MeanPooling()
        elif pooling_type == 'max':
            self.pooling = MaxPooling()
        else:
            raise ValueError(f"不支持的池化类型: {pooling_type}")

        self.dropout = nn.Dropout(dropout_prob)
        self.classifier = nn.Linear(hidden_size, num_labels)

    def forward(self, input_ids, attention_mask=None, token_type_ids=None, labels=None):
        """
        Args:
            input_ids: (batch_size, seq_len)
            attention_mask: (batch_size, seq_len)
            token_type_ids: (batch_size, seq_len), 可选
            labels: (batch_size,), 可选

        Returns:
            如果提供labels，返回 (loss, logits)
            否则返回 logits
        """
        # BERT编码
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask,
            token_type_ids=token_type_ids
        )

        # 获取序列输出
        sequence_output = outputs.last_hidden_state  # (batch, seq_len, hidden)

        # 自定义池化
        pooled_output = self.pooling(sequence_output, attention_mask)

        # Dropout + 分类
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)

        # 计算损失
        loss = None
        if labels is not None:
            loss_fct = nn.CrossEntropyLoss()
            loss = loss_fct(logits.view(-1, self.num_labels), labels.view(-1))

        # 返回结果（模仿transformers的输出格式）
        class Output:
            def __init__(self, loss, logits):
                self.loss = loss
                self.logits = logits

        return Output(loss=loss, logits=logits)

    def save_pretrained(self, save_directory):
        """保存模型"""
        import os
        os.makedirs(save_directory, exist_ok=True)

        # 保存BERT部分
        self.bert.save_pretrained(save_directory)

        # 保存分类器和池化层
        model_path = os.path.join(save_directory, 'custom_layers.pt')
        torch.save({
            'pooling_state_dict': self.pooling.state_dict(),
            'classifier_state_dict': self.classifier.state_dict(),
            'dropout_state_dict': self.dropout.state_dict(),
            'num_labels': self.num_labels,
            'pooling_type': self.pooling.__class__.__name__,
        }, model_path)

    @classmethod
    def from_pretrained(cls, model_path, pooling_type='attention'):
        """加载模型"""
        from transformers import BertModel
        import os

        # 加载BERT
        bert = BertModel.from_pretrained(model_path)

        # 加载自定义层
        custom_layers_path = os.path.join(model_path, 'custom_layers.pt')
        if os.path.exists(custom_layers_path):
            checkpoint = torch.load(custom_layers_path)
            num_labels = checkpoint['num_labels']

            # 创建模型
            class DummyBaseModel:
                def __init__(self, bert, config):
                    self.bert = bert
                    self.config = config

            base_model = DummyBaseModel(bert, bert.config)
            model = cls(base_model, num_labels=num_labels, pooling_type=pooling_type)

            # 加载权重
            model.pooling.load_state_dict(checkpoint['pooling_state_dict'])
            model.classifier.load_state_dict(checkpoint['classifier_state_dict'])
            model.dropout.load_state_dict(checkpoint['dropout_state_dict'])

            return model
        else:
            raise FileNotFoundError(f"找不到自定义层文件: {custom_layers_path}")
