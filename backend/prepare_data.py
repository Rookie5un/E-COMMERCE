"""
三分类训练数据构建脚本。

用法:
1. 将二分类源数据转换为统一的 `content,label` 结构。
2. 自动挑出一批适合人工复核的 neutral 候选。
3. 将人工复核通过的 neutral 合并回最终三分类训练集。

示例:
python prepare_data.py \
  --input_file ../online_shopping_10_cats.csv \
  --binary_output data/train_binary_base.csv \
  --neutral_candidates_output data/neutral_candidates.csv

python prepare_data.py \
  --input_file data/train_binary_base.csv \
  --reviewed_neutral_file data/neutral_reviewed.csv \
  --output_file data/train_multiclass.csv
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


LABEL_MAP = {
    0: "negative",
    1: "positive",
    "0": "negative",
    "1": "positive",
    "negative": "negative",
    "neutral": "neutral",
    "positive": "positive",
}

POSITIVE_HINTS = ("满意", "推荐", "喜欢", "不错", "好用", "给力", "值得", "超值")
NEGATIVE_HINTS = ("失望", "后悔", "问题", "差", "卡顿", "发热", "故障", "糟糕")
NEUTRAL_HINTS = (
    "还可以",
    "一般般",
    "中规中矩",
    "凑合",
    "符合预期",
    "没有特别",
    "整体还行",
    "普普通通",
    "够用",
    "一般",
)
BALANCE_HINTS = ("但是", "不过", "只是", "然而", "整体", "还算")
DEFAULT_MIN_CONTENT_LENGTH = 5
DEFAULT_MAX_CONTENT_LENGTH = 500


def normalize_source_dataframe(input_file: str | Path) -> pd.DataFrame:
    """统一不同源数据格式到 content,label 两列。"""
    dataframe = pd.read_csv(input_file)

    if {"content", "label"}.issubset(dataframe.columns):
        normalized = dataframe[["content", "label"]].copy()
    elif {"review", "label"}.issubset(dataframe.columns):
        normalized = dataframe.rename(columns={"review": "content"})[["content", "label"]].copy()
    else:
        raise ValueError("输入文件必须包含 `content,label` 或 `review,label` 列")

    normalized["content"] = normalized["content"].fillna("").astype(str).str.replace("\ufeff", "", regex=False).str.strip()
    normalized["label"] = normalized["label"].map(LABEL_MAP).fillna(normalized["label"].astype(str).str.strip().str.lower())
    content_lengths = normalized["content"].str.len()
    normalized = normalized[
        (content_lengths >= DEFAULT_MIN_CONTENT_LENGTH)
        & (content_lengths <= DEFAULT_MAX_CONTENT_LENGTH)
    ]
    normalized = normalized.drop_duplicates(subset=["content"]).reset_index(drop=True)
    normalized = normalized[normalized["label"].isin({"positive", "negative", "neutral"})]
    return normalized


def score_neutral_candidate(text: str) -> tuple[int, int, int]:
    """分数越大越适合作为 neutral 人工复核候选。"""
    positive_hits = sum(1 for word in POSITIVE_HINTS if word in text)
    negative_hits = sum(1 for word in NEGATIVE_HINTS if word in text)
    neutral_hits = sum(1 for word in NEUTRAL_HINTS if word in text)
    balance_hits = sum(1 for word in BALANCE_HINTS if word in text)
    polarity_gap = abs(positive_hits - negative_hits)
    return (
        neutral_hits + balance_hits,
        -polarity_gap,
        -abs(len(text) - 40),
    )


def build_neutral_candidates(dataframe: pd.DataFrame, candidate_count: int) -> pd.DataFrame:
    """抽取需要人工复核的 neutral 候选。"""
    candidates = dataframe.copy()
    candidates = candidates[candidates["label"] != "neutral"].copy()
    candidates["candidate_score"] = candidates["content"].map(score_neutral_candidate)
    candidates = candidates.sort_values("candidate_score", ascending=False).head(candidate_count).copy()
    candidates["suggested_label"] = "neutral"
    candidates["reviewed_label"] = ""
    candidates["notes"] = ""
    return candidates[["content", "label", "suggested_label", "reviewed_label", "notes"]]


def load_reviewed_neutral_dataframe(reviewed_file: str | Path) -> pd.DataFrame:
    """加载人工复核后的 neutral 数据。"""
    reviewed = pd.read_csv(reviewed_file)
    if "content" not in reviewed.columns:
        raise ValueError("人工复核文件缺少 `content` 列")

    label_column = "reviewed_label" if "reviewed_label" in reviewed.columns else "label"
    reviewed = reviewed[["content", label_column]].rename(columns={label_column: "label"})
    reviewed["content"] = reviewed["content"].fillna("").astype(str).str.strip()
    reviewed["label"] = reviewed["label"].fillna("").astype(str).str.strip().str.lower()
    content_lengths = reviewed["content"].str.len()
    reviewed = reviewed[
        (content_lengths >= DEFAULT_MIN_CONTENT_LENGTH)
        & (content_lengths <= DEFAULT_MAX_CONTENT_LENGTH)
        & (reviewed["label"] == "neutral")
    ]
    reviewed = reviewed.drop_duplicates(subset=["content"]).reset_index(drop=True)
    return reviewed


def write_dataframe(dataframe: pd.DataFrame, file_path: str | Path) -> None:
    path = Path(file_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(path, index=False, encoding="utf-8-sig")


def main() -> int:
    parser = argparse.ArgumentParser(description="构建三分类训练数据")
    parser.add_argument("--input_file", required=True, help="原始 CSV 文件路径")
    parser.add_argument(
        "--binary_output",
        default="data/train_binary_base.csv",
        help="标准化后的基础数据输出路径",
    )
    parser.add_argument(
        "--neutral_candidates_output",
        default="data/neutral_candidates.csv",
        help="待人工复核的 neutral 候选文件路径",
    )
    parser.add_argument(
        "--reviewed_neutral_file",
        help="人工复核后的 neutral CSV 文件路径",
    )
    parser.add_argument(
        "--output_file",
        default="data/train_multiclass.csv",
        help="最终三分类训练集输出路径",
    )
    parser.add_argument(
        "--candidate_count",
        type=int,
        default=1500,
        help="输出多少条 neutral 候选",
    )
    args = parser.parse_args()

    print("读取源数据...")
    base_dataframe = normalize_source_dataframe(args.input_file)
    print(f"标准化后样本数: {len(base_dataframe)}")
    print(f"标签分布: {base_dataframe['label'].value_counts().to_dict()}")

    write_dataframe(base_dataframe, args.binary_output)
    print(f"基础数据已输出到: {args.binary_output}")

    neutral_candidates = build_neutral_candidates(base_dataframe, args.candidate_count)
    write_dataframe(neutral_candidates, args.neutral_candidates_output)
    print(f"Neutral 候选已输出到: {args.neutral_candidates_output}")

    if not args.reviewed_neutral_file:
        print("\n下一步:")
        print("1. 打开 neutral 候选文件，人工复核 reviewed_label 列。")
        print("2. 仅保留 reviewed_label=neutral 的样本。")
        print("3. 重新执行本脚本并传入 --reviewed_neutral_file。")
        return 0

    reviewed_neutral = load_reviewed_neutral_dataframe(args.reviewed_neutral_file)
    print(f"人工复核 neutral 样本数: {len(reviewed_neutral)}")

    final_dataframe = base_dataframe.copy()
    reviewed_lookup = reviewed_neutral.set_index("content")["label"].to_dict()
    final_dataframe["label"] = final_dataframe["content"].map(reviewed_lookup).fillna(final_dataframe["label"])
    new_neutral_rows = reviewed_neutral[~reviewed_neutral["content"].isin(final_dataframe["content"])]
    if not new_neutral_rows.empty:
        final_dataframe = pd.concat([final_dataframe, new_neutral_rows], ignore_index=True)

    final_dataframe = final_dataframe[["content", "label"]].copy()
    final_dataframe = final_dataframe.sort_values("label").reset_index(drop=True)

    write_dataframe(final_dataframe, args.output_file)
    print(f"三分类训练数据已输出到: {args.output_file}")
    print(f"最终标签分布: {final_dataframe['label'].value_counts().to_dict()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
