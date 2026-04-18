import re
import jieba
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TextProcessor:
    """文本预处理器"""

    def __init__(self):
        # 加载停用词
        self.stopwords = self._load_stopwords()

    def clean_text(self, text):
        """清洗文本"""
        if not text:
            return ''

        # 去除HTML标签
        text = re.sub(r'<[^>]+>', '', text)

        # 去除URL
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)

        # 去除特殊字符，保留中文、英文、数字和基本标点
        text = re.sub(r'[^\u4e00-\u9fa5a-zA-Z0-9\s,.!?，。！？、]', '', text)

        # 去除多余空白
        text = re.sub(r'\s+', ' ', text)

        return text.strip()

    def tokenize(self, text):
        """分词"""
        if not text:
            return []

        # 使用jieba分词
        words = jieba.cut(text)

        # 过滤停用词和单字符
        tokens = [
            word.strip() for word in words
            if word.strip() and len(word.strip()) > 1 and word not in self.stopwords
        ]

        return tokens

    def _load_stopwords(self):
        """加载停用词表"""
        stopwords = set()

        # 尝试从文件加载
        stopwords_file = Path(__file__).parent.parent.parent / 'data' / 'stopwords.txt'

        if stopwords_file.exists():
            try:
                with open(stopwords_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        word = line.strip()
                        if word:
                            stopwords.add(word)
                logger.info(f'从文件加载停用词: {len(stopwords)} 个')
                return stopwords
            except Exception as e:
                logger.warning(f'加载停用词文件失败: {e}，使用默认停用词表')

        # 回退到基础停用词列表
        stopwords = {
            '的', '了', '在', '是', '我', '有', '和', '就', '不', '人',
            '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去',
            '你', '会', '着', '没有', '看', '好', '自己', '这', '那', '个',
            '们', '中', '来', '为', '能', '对', '生', '和', '与', '及',
            '以', '而', '或', '等', '但', '却', '因', '由', '于', '从'
        }
        logger.info(f'使用默认停用词表: {len(stopwords)} 个')

        return stopwords
