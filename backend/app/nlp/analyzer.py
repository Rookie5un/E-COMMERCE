"""
NLP分析模块 - 基于RoBERTa-wwm的情感分析
"""

import numpy as np
from typing import List, Dict
import logging

try:
    import torch
except ImportError:
    torch = None

try:
    from transformers import BertTokenizer, BertForSequenceClassification
except ImportError:
    BertTokenizer = None
    BertForSequenceClassification = None

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """情感分析器 - 使用RoBERTa-wwm模型"""

    def __init__(self, model_path='hfl/chinese-roberta-wwm-ext'):
        """
        初始化情感分析器

        Args:
            model_path: 模型路径，可以是：
                - Hugging Face模型名: 'hfl/chinese-roberta-wwm-ext'
                - 本地模型路径: './data/models/roberta-sentiment'
        """
        self.model_path = model_path
        self.max_length = 512
        self.model_loaded = False
        self.tokenizer = None
        self.model = None

        if torch is not None:
            self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        else:
            self.device = 'cpu'

        self.ml_backend_ready = all([
            torch is not None,
            BertTokenizer is not None,
            BertForSequenceClassification is not None
        ])

        if not self.ml_backend_ready:
            logger.warning("未安装 torch/transformers，情感分析器将使用规则兜底模式。")
            return

        try:
            logger.info(f"加载模型: {model_path}")
            self.tokenizer = BertTokenizer.from_pretrained(model_path)
            self.model = BertForSequenceClassification.from_pretrained(
                model_path,
                num_labels=3
            )
            self.model.to(self.device)
            self.model.eval()
            self.model_loaded = True
            logger.info(f"模型加载成功，使用设备: {self.device}")
        except Exception as e:
            logger.warning(f"模型加载失败，切换到规则兜底模式: {str(e)}")

    def predict(self, text: str) -> Dict:
        """
        预测单条文本的情感

        Args:
            text: 评论文本

        Returns:
            {
                'label': 'positive' | 'neutral' | 'negative',
                'confidence': float,
                'probabilities': {
                    'positive': float,
                    'neutral': float,
                    'negative': float
                }
            }
        """
        if not text or not text.strip():
            return self._default_result()

        if not self.model_loaded:
            return self._rule_based_predict(text)

        try:
            # 分词和编码
            inputs = self.tokenizer(
                text,
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )

            # 移动到设备
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # 预测
            with torch.no_grad():
                outputs = self.model(**inputs)
                logits = outputs.logits
                probs = torch.softmax(logits, dim=-1)

            # 解析结果
            probs_np = probs.cpu().numpy()[0]
            label_idx = np.argmax(probs_np)

            labels = ['negative', 'neutral', 'positive']  # 0:负向, 1:中性, 2:正向

            return {
                'label': labels[label_idx],
                'confidence': float(probs_np[label_idx]),
                'probabilities': {
                    'positive': float(probs_np[2]),
                    'neutral': float(probs_np[1]),
                    'negative': float(probs_np[0])
                }
            }
        except Exception as e:
            logger.error(f"预测失败: {str(e)}")
            return self._default_result()

    def batch_predict(self, texts: List[str], batch_size: int = 32) -> List[Dict]:
        """
        批量预测

        Args:
            texts: 文本列表
            batch_size: 批次大小

        Returns:
            预测结果列表
        """
        results = []

        if not self.model_loaded:
            return [self._rule_based_predict(text) for text in texts]

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]

            try:
                # 批量编码
                inputs = self.tokenizer(
                    batch_texts,
                    max_length=self.max_length,
                    padding=True,
                    truncation=True,
                    return_tensors='pt'
                )

                inputs = {k: v.to(self.device) for k, v in inputs.items()}

                # 批量预测
                with torch.no_grad():
                    outputs = self.model(**inputs)
                    logits = outputs.logits
                    probs = torch.softmax(logits, dim=-1)

                probs_np = probs.cpu().numpy()
                labels = ['negative', 'neutral', 'positive']

                # 解析每条结果
                for j in range(len(batch_texts)):
                    label_idx = np.argmax(probs_np[j])
                    results.append({
                        'label': labels[label_idx],
                        'confidence': float(probs_np[j][label_idx]),
                        'probabilities': {
                            'positive': float(probs_np[j][2]),
                            'neutral': float(probs_np[j][1]),
                            'negative': float(probs_np[j][0])
                        }
                    })

                logger.info(f"批次 {i//batch_size + 1} 完成，处理 {len(batch_texts)} 条")

            except Exception as e:
                logger.error(f"批次预测失败: {str(e)}")
                # 失败的批次使用默认结果
                for _ in batch_texts:
                    results.append(self._default_result())

        return results

    def _rule_based_predict(self, text: str) -> Dict:
        """规则兜底预测（无深度学习依赖时使用）"""
        negative_words = {'卡顿', '发热', '故障', '差', '烂', '坏', '慢', '失望', '后悔', '问题'}
        positive_words = {'好', '满意', '喜欢', '流畅', '清晰', '给力', '推荐', '不错', '划算'}

        neg_score = sum(1 for w in negative_words if w in text)
        pos_score = sum(1 for w in positive_words if w in text)

        if neg_score > pos_score:
            return {
                'label': 'negative',
                'confidence': 0.60,
                'probabilities': {
                    'positive': 0.15,
                    'neutral': 0.25,
                    'negative': 0.60
                }
            }
        if pos_score > neg_score:
            return {
                'label': 'positive',
                'confidence': 0.60,
                'probabilities': {
                    'positive': 0.60,
                    'neutral': 0.25,
                    'negative': 0.15
                }
            }
        return self._default_result()

    def _default_result(self) -> Dict:
        """默认结果（预测失败时使用）"""
        return {
            'label': 'neutral',
            'confidence': 0.33,
            'probabilities': {
                'positive': 0.33,
                'neutral': 0.34,
                'negative': 0.33
            }
        }


class AspectExtractor:
    """功能点提取器"""

    def __init__(self):
        """初始化功能点提取器"""
        # 电商常见功能点词典（可扩展）
        self.aspect_dict = {
            # 手机数码类
            '屏幕': ['屏幕', '显示', '分辨率', '屏', '显示屏'],
            '续航': ['续航', '电池', '耗电', '电量', '充电'],
            '性能': ['性能', '速度', '流畅', '卡顿', '运行'],
            '拍照': ['拍照', '相机', '摄像', '照片', '镜头'],
            '外观': ['外观', '颜值', '设计', '手感', '做工'],
            '系统': ['系统', '软件', '界面', 'UI', '操作'],
            '散热': ['散热', '发热', '温度', '烫'],
            '音质': ['音质', '音效', '声音', '扬声器', '耳机'],

            # 通用类
            '价格': ['价格', '性价比', '便宜', '贵', '值'],
            '质量': ['质量', '品质', '做工', '材质'],
            '物流': ['物流', '快递', '配送', '送货', '包装'],
            '服务': ['服务', '客服', '态度', '售后'],
        }

        # 构建反向索引
        self.word_to_aspect = {}
        for aspect, words in self.aspect_dict.items():
            for word in words:
                self.word_to_aspect[word] = aspect

    def extract(self, text: str, tokens: List[str] = None) -> List[Dict]:
        """
        提取功能点

        Args:
            text: 原始文本
            tokens: 分词结果（可选）

        Returns:
            [
                {
                    'aspect': str,
                    'normalized_aspect': str,
                    'start': int,
                    'end': int,
                    'confidence': float
                }
            ]
        """
        aspects = []
        seen_aspects = set()

        # 使用词典匹配
        for word, aspect in self.word_to_aspect.items():
            if word in text:
                # 避免重复
                if aspect not in seen_aspects:
                    start = text.find(word)
                    aspects.append({
                        'aspect': word,
                        'normalized_aspect': aspect,
                        'start': start,
                        'end': start + len(word),
                        'confidence': 0.95
                    })
                    seen_aspects.add(aspect)

        return aspects

    def add_aspect(self, aspect_name: str, keywords: List[str]):
        """
        添加新的功能点

        Args:
            aspect_name: 功能点名称
            keywords: 关键词列表
        """
        self.aspect_dict[aspect_name] = keywords
        for word in keywords:
            self.word_to_aspect[word] = aspect_name


class IssueExtractor:
    """问题挖掘器 - 基于TextRank"""

    def __init__(self):
        """初始化问题挖掘器"""
        import jieba.analyse
        self.jieba_analyse = jieba.analyse

        # 负面词汇（用于增强负面问题识别）
        self.negative_words = {
            '卡顿', '发热', '烫', '差', '坏', '烂', '假', '次',
            '慢', '短', '小', '少', '贵', '不好', '失望', '后悔',
            '问题', '故障', '损坏', '破损', '漏', '裂', '掉',
            '不值', '不行', '垃圾', '骗人', '虚假'
        }

    def extract_keywords(self, texts: List[str], top_k: int = 20) -> List[Dict]:
        """
        使用TextRank提取关键词

        Args:
            texts: 负面评论列表
            top_k: 返回前k个关键词

        Returns:
            [
                {
                    'keyword': str,
                    'score': float,
                    'frequency': int
                }
            ]
        """
        if not texts:
            return []

        # 合并所有文本
        combined_text = ' '.join(texts)

        # 使用TextRank提取关键词
        keywords_with_weight = self.jieba_analyse.textrank(
            combined_text,
            topK=top_k * 2,  # 提取更多，后续过滤
            withWeight=True
        )

        # 统计频次
        keyword_freq = {}
        for text in texts:
            for keyword, weight in keywords_with_weight:
                if keyword in text:
                    keyword_freq[keyword] = keyword_freq.get(keyword, 0) + 1

        # 构建结果
        results = []
        for keyword, weight in keywords_with_weight:
            # 过滤单字和停用词
            if len(keyword) < 2:
                continue

            # 增强负面词汇的权重
            if keyword in self.negative_words:
                weight *= 1.5

            results.append({
                'keyword': keyword,
                'score': float(weight),
                'frequency': keyword_freq.get(keyword, 0)
            })

        # 按频次和权重排序
        results.sort(key=lambda x: (x['frequency'], x['score']), reverse=True)

        return results[:top_k]

    def extract_with_aspect(self, texts: List[str], aspects: List[str]) -> Dict[str, List[str]]:
        """
        按功能点提取问题关键词

        Args:
            texts: 负面评论列表
            aspects: 功能点列表

        Returns:
            {
                'aspect_name': ['keyword1', 'keyword2', ...]
            }
        """
        aspect_issues = {aspect: [] for aspect in aspects}

        for text in texts:
            # 提取关键词
            keywords = self.jieba_analyse.textrank(text, topK=5)

            # 匹配功能点
            for aspect in aspects:
                if aspect in text:
                    aspect_issues[aspect].extend(keywords)

        # 去重
        for aspect in aspect_issues:
            aspect_issues[aspect] = list(set(aspect_issues[aspect]))

        return aspect_issues
