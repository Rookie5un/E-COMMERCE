"""
快速测试脚本 - 测试NLP分析功能

使用方法:
python test_nlp.py
"""

from app.nlp.analyzer import SentimentAnalyzer, AspectExtractor, IssueExtractor
from app.nlp.text_processor import TextProcessor


def test_sentiment_analysis():
    """测试情感分析"""
    print("=" * 60)
    print("测试情感分析")
    print("=" * 60)

    # 初始化分析器（如果没有安装torch，会使用规则模式）
    analyzer = SentimentAnalyzer()

    test_cases = [
        "这个手机很好用，拍照清晰，续航给力！",
        "屏幕显示效果不错，但是有点卡顿",
        "电池续航太差了，用一天就没电",
        "还可以吧，没有特别惊艳",
        "性价比超高，值得购买",
        "发热严重，玩游戏很烫手"
    ]

    for text in test_cases:
        result = analyzer.predict(text)
        print(f"\n文本: {text}")
        print(f"情感: {result['label']}")
        print(f"置信度: {result['confidence']:.2f}")
        print(f"概率分布: 正向={result['probabilities']['positive']:.2f}, "
              f"中性={result['probabilities']['neutral']:.2f}, "
              f"负向={result['probabilities']['negative']:.2f}")


def test_aspect_extraction():
    """测试功能点提取"""
    print("\n" + "=" * 60)
    print("测试功能点提取")
    print("=" * 60)

    extractor = AspectExtractor()
    processor = TextProcessor()

    test_cases = [
        "屏幕显示效果很好，续航也不错",
        "拍照清晰，但是发热有点严重",
        "性价比高，物流快，服务态度好",
        "系统流畅，外观漂亮，音质也可以"
    ]

    for text in test_cases:
        tokens = processor.tokenize(text)
        aspects = extractor.extract(text, tokens)

        print(f"\n文本: {text}")
        print(f"分词: {' / '.join(tokens)}")
        print(f"功能点: {[a['normalized_aspect'] for a in aspects]}")


def test_issue_extraction():
    """测试问题挖掘"""
    print("\n" + "=" * 60)
    print("测试问题挖掘")
    print("=" * 60)

    extractor = IssueExtractor()

    negative_reviews = [
        "电池续航太差了，用一天就没电",
        "发热严重，玩游戏很烫手",
        "屏幕容易碎，质量不行",
        "卡顿严重，运行很慢",
        "拍照效果差，不清晰",
        "系统bug多，经常死机",
        "续航时间短，充电慢",
        "发热问题严重，影响使用"
    ]

    issues = extractor.extract_keywords(negative_reviews, top_k=10)

    print(f"\n负面评论数: {len(negative_reviews)}")
    print("\n问题关键词排行:")
    for i, issue in enumerate(issues, 1):
        print(f"{i}. {issue['keyword']} - 频次:{issue['frequency']}, 权重:{issue['score']:.3f}")


def test_text_processing():
    """测试文本预处理"""
    print("\n" + "=" * 60)
    print("测试文本预处理")
    print("=" * 60)

    processor = TextProcessor()

    test_cases = [
        "这个手机<b>很好用</b>！！！",
        "   屏幕   显示   效果   不错   ",
        "访问 https://example.com 查看详情",
        "价格：￥2999，性价比高！"
    ]

    for text in test_cases:
        cleaned = processor.clean_text(text)
        tokens = processor.tokenize(cleaned)

        print(f"\n原文: {text}")
        print(f"清洗后: {cleaned}")
        print(f"分词: {' / '.join(tokens)}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("NLP分析功能测试")
    print("=" * 60)

    try:
        # 测试文本预处理
        test_text_processing()

        # 测试情感分析
        test_sentiment_analysis()

        # 测试功能点提取
        test_aspect_extraction()

        # 测试问题挖掘
        test_issue_extraction()

        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)

    except Exception as e:
        print(f"\n测试失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
