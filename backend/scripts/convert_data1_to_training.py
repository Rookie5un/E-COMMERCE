"""
将 data1 目录的餐厅评论数据转换为三分类训练格式

映射规则：
- star >= 4: positive (正面)
- star == 3: neutral (中性)
- star <= 2: negative (负面)
"""

import pandas as pd
import sys
from pathlib import Path

# 添加 backend 到路径以导入工具函数
sys.path.insert(0, str(Path(__file__).parent.parent))
from training_data_utils import TRAINING_LABELS, normalize_training_dataframe


def convert_star_to_label(star, neutral_range='strict'):
    """
    将星级评分转换为三分类标签

    Args:
        star: 星级评分
        neutral_range: 中性范围策略
            - 'strict': 只有 3.0 为中性
            - 'relaxed': 2.5-3.5 为中性
    """
    try:
        star_value = float(star)

        if neutral_range == 'relaxed':
            # 宽松策略：2.5-3.5 为中性
            if star_value >= 4.0:
                return 'positive'
            elif 2.5 <= star_value <= 3.5:
                return 'neutral'
            else:  # star_value < 2.5
                return 'negative'
        else:
            # 严格策略：只有 3.0 为中性
            if star_value >= 4.0:
                return 'positive'
            elif star_value == 3.0:
                return 'neutral'
            else:  # star_value <= 2.0
                return 'negative'
    except (ValueError, TypeError):
        return None


def process_data1_file(input_file, output_file, include_stars=None, neutral_range='strict'):
    """
    处理 data1 数据文件

    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径
        include_stars: 只包含指定星级的评论，None 表示包含所有
        neutral_range: 中性范围策略 ('strict' 或 'relaxed')
    """
    print(f'读取文件: {input_file}')
    df = pd.read_csv(input_file, encoding='utf-8')

    print(f'原始数据: {len(df)} 条')
    print(f'列名: {df.columns.tolist()}')

    # 检查必要的列
    if 'review' not in df.columns or 'star' not in df.columns:
        raise ValueError('数据文件必须包含 review 和 star 列')

    # 过滤空评论
    df = df[df['review'].notna() & (df['review'].astype(str).str.strip() != '')]
    print(f'过滤空评论后: {len(df)} 条')

    # 如果指定了星级过滤
    if include_stars is not None:
        df = df[df['star'].isin(include_stars)]
        print(f'过滤星级 {include_stars} 后: {len(df)} 条')

    # 转换为训练格式
    df['content'] = df['review'].astype(str).str.strip()
    df['label'] = df['star'].apply(lambda x: convert_star_to_label(x, neutral_range))

    # 过滤无效标签
    df = df[df['label'].notna()]

    # 只保留需要的列
    result_df = df[['content', 'label']].copy()

    # 去重
    original_count = len(result_df)
    result_df = result_df.drop_duplicates(subset=['content'], keep='first')
    removed_count = original_count - len(result_df)

    if removed_count > 0:
        print(f'去除重复: {removed_count} 条')

    # 统计标签分布
    label_counts = result_df['label'].value_counts()
    print(f'\n标签分布:')
    for label in TRAINING_LABELS:
        count = label_counts.get(label, 0)
        print(f'  {label}: {count}')

    # 保存
    result_df.to_csv(output_file, index=False, encoding='utf-8')
    print(f'\n已保存到: {output_file}')
    print(f'总计: {len(result_df)} 条')

    return result_df


def merge_training_data(original_file, new_file, output_file):
    """合并原有训练集和新数据"""
    print(f'\n合并训练数据...')

    # 读取原有数据
    df_original = pd.read_csv(original_file, encoding='utf-8')
    print(f'原有训练集: {len(df_original)} 条')

    # 读取新数据
    df_new = pd.read_csv(new_file, encoding='utf-8')
    print(f'新数据: {len(df_new)} 条')

    # 合并
    df_merged = pd.concat([df_original, df_new], ignore_index=True)
    print(f'合并后: {len(df_merged)} 条')

    # 去重
    original_count = len(df_merged)
    df_merged = df_merged.drop_duplicates(subset=['content'], keep='first')
    removed_count = original_count - len(df_merged)

    if removed_count > 0:
        print(f'去除重复: {removed_count} 条')

    # 统计标签分布
    label_counts = df_merged['label'].value_counts()
    print(f'\n合并后标签分布:')
    for label in TRAINING_LABELS:
        count = label_counts.get(label, 0)
        print(f'  {label}: {count}')

    # 保存
    df_merged.to_csv(output_file, index=False, encoding='utf-8')
    print(f'\n已保存到: {output_file}')
    print(f'总计: {len(df_merged)} 条')


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='转换 data1 数据为训练格式')
    parser.add_argument('--input', type=str, default='data1/train.csv',
                        help='输入文件路径')
    parser.add_argument('--output', type=str, default='backend/data/data1_converted.csv',
                        help='输出文件路径')
    parser.add_argument('--only-neutral', action='store_true',
                        help='只提取中评 (star=3)')
    parser.add_argument('--neutral-range', type=str, default='strict',
                        choices=['strict', 'relaxed'],
                        help='中性范围策略: strict(仅3.0) 或 relaxed(2.5-3.5)')
    parser.add_argument('--merge-with', type=str,
                        help='合并到指定的训练集文件')
    parser.add_argument('--merge-output', type=str,
                        help='合并后的输出文件')

    args = parser.parse_args()

    # 转换数据
    include_stars = [3.0] if args.only_neutral else None
    result_df = process_data1_file(args.input, args.output, include_stars, args.neutral_range)

    # 如果需要合并
    if args.merge_with:
        merge_output = args.merge_output or 'backend/data/train_multiclass_merged.csv'
        merge_training_data(args.merge_with, args.output, merge_output)
