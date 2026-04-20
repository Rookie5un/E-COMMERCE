"""
通过组合好评和差评片段来合成中评

策略：
1. 从好评中提取正面句子
2. 从差评中提取负面句子
3. 随机组合成"有好有坏"的中评
4. 去重确保没有重复
"""

import pandas as pd
import random
import re
from pathlib import Path
import sys

# 添加 backend 到路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def split_sentences(text):
    """将文本分割成句子"""
    # 按照中文标点符号分割
    sentences = re.split(r'[。！？；\n]+', str(text))
    # 过滤空句子和过短的句子
    sentences = [s.strip() for s in sentences if len(s.strip()) > 5]
    return sentences


def load_reviews_by_star(file_path, star_values):
    """加载指定星级的评论"""
    df = pd.read_csv(file_path, encoding='utf-8')
    df = df[df['star'].isin(star_values) & df['review'].notna()]
    reviews = df['review'].astype(str).tolist()
    return reviews


def synthesize_neutral_review(positive_sentences, negative_sentences):
    """
    合成一条中评

    策略：随机选择1-2个正面句子 + 1-2个负面句子
    """
    # 随机选择句子数量
    n_pos = random.randint(1, 2)
    n_neg = random.randint(1, 2)

    # 随机选择句子
    pos_selected = random.sample(positive_sentences, min(n_pos, len(positive_sentences)))
    neg_selected = random.sample(negative_sentences, min(n_neg, len(negative_sentences)))

    # 随机组合顺序
    all_sentences = pos_selected + neg_selected
    random.shuffle(all_sentences)

    # 用逗号或句号连接
    connectors = ['，', '。', '，但是', '，不过']
    result = all_sentences[0]
    for sent in all_sentences[1:]:
        connector = random.choice(connectors)
        result += connector + sent

    # 确保以句号结尾
    if not result.endswith('。'):
        result += '。'

    return result


def generate_neutral_reviews(input_file, output_file, num_samples=5000, seed=42):
    """
    生成合成的中评

    Args:
        input_file: data1 数据文件
        output_file: 输出文件
        num_samples: 生成数量
        seed: 随机种子
    """
    random.seed(seed)

    print(f'读取数据: {input_file}')

    # 加载好评和差评
    positive_reviews = load_reviews_by_star(input_file, [4.0, 5.0])
    negative_reviews = load_reviews_by_star(input_file, [1.0, 2.0])

    print(f'好评数量: {len(positive_reviews)}')
    print(f'差评数量: {len(negative_reviews)}')

    # 分割成句子
    print('\n分割句子...')
    positive_sentences = []
    for review in positive_reviews:
        positive_sentences.extend(split_sentences(review))

    negative_sentences = []
    for review in negative_reviews:
        negative_sentences.extend(split_sentences(review))

    print(f'正面句子: {len(positive_sentences)}')
    print(f'负面句子: {len(negative_sentences)}')

    # 生成合成评论
    print(f'\n生成 {num_samples} 条合成中评...')
    synthesized_reviews = []
    seen_reviews = set()  # 用于去重

    attempts = 0
    max_attempts = num_samples * 3  # 最多尝试3倍次数

    while len(synthesized_reviews) < num_samples and attempts < max_attempts:
        attempts += 1

        # 合成一条评论
        review = synthesize_neutral_review(positive_sentences, negative_sentences)

        # 去重
        if review not in seen_reviews:
            seen_reviews.add(review)
            synthesized_reviews.append(review)

        if len(synthesized_reviews) % 500 == 0:
            print(f'  已生成: {len(synthesized_reviews)} / {num_samples}')

    print(f'\n成功生成 {len(synthesized_reviews)} 条不重复的中评')

    # 保存为训练格式
    df = pd.DataFrame({
        'content': synthesized_reviews,
        'label': ['neutral'] * len(synthesized_reviews)
    })

    df.to_csv(output_file, index=False, encoding='utf-8')
    print(f'已保存到: {output_file}')

    # 显示示例
    print('\n示例合成评论:')
    for i, review in enumerate(synthesized_reviews[:5], 1):
        print(f'{i}. {review}')

    return df


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='合成中评数据')
    parser.add_argument('--input', type=str, default='data1/train.csv',
                        help='输入文件路径')
    parser.add_argument('--output', type=str, default='backend/data/synthesized_neutral.csv',
                        help='输出文件路径')
    parser.add_argument('--num-samples', type=int, default=5000,
                        help='生成数量')
    parser.add_argument('--seed', type=int, default=42,
                        help='随机种子')

    args = parser.parse_args()

    generate_neutral_reviews(
        args.input,
        args.output,
        args.num_samples,
        args.seed
    )
