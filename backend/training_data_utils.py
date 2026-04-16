"""
训练数据工具。

统一三分类标签映射、CSV 校验和数据摘要，避免训练/评估脚本各自维护一套规则。
"""

from __future__ import annotations

from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

TRAINING_LABELS = ("negative", "neutral", "positive")
LABEL_TO_ID = {label: index for index, label in enumerate(TRAINING_LABELS)}
ID_TO_LABEL = {index: label for label, index in LABEL_TO_ID.items()}
REQUIRED_COLUMNS = ("content", "label")


class DatasetValidationError(ValueError):
    """训练数据不满足三分类要求时抛出。"""


@dataclass
class DatasetSummary:
    """训练数据摘要，便于打印或写入 JSON。"""

    file_path: str
    total_rows: int
    unique_contents: int
    duplicate_contents: int
    empty_contents: int
    missing_labels: int
    label_counts: dict[str, int]
    min_length: int
    max_length: int
    average_length: float
    short_contents: int
    long_contents: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def read_training_csv(file_path: str | Path) -> pd.DataFrame:
    """读取训练数据，并标准化常见脏值。"""
    dataframe = pd.read_csv(file_path)
    return normalize_training_dataframe(dataframe)


def normalize_training_dataframe(dataframe: pd.DataFrame) -> pd.DataFrame:
    """规范化训练数据列和内容，便于后续统一校验。"""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in dataframe.columns]
    if missing_columns:
        raise DatasetValidationError(
            f"训练数据缺少必要列: {', '.join(missing_columns)}"
        )

    normalized = dataframe.copy()
    normalized["content"] = normalized["content"].fillna("").astype(str).str.replace("\ufeff", "", regex=False).str.strip()
    normalized["label"] = normalized["label"].fillna("").astype(str).str.strip().str.lower()
    return normalized


def build_dataset_summary(
    dataframe: pd.DataFrame,
    file_path: str | Path,
    min_content_length: int = 5,
    max_content_length: int = 500,
) -> DatasetSummary:
    """构建训练数据摘要。"""
    normalized = normalize_training_dataframe(dataframe)
    content_lengths = normalized["content"].str.len()
    label_counts = Counter(label for label in normalized["label"] if label)

    return DatasetSummary(
        file_path=str(file_path),
        total_rows=len(normalized),
        unique_contents=normalized["content"].nunique(dropna=True),
        duplicate_contents=int(normalized["content"].duplicated().sum()),
        empty_contents=int((content_lengths == 0).sum()),
        missing_labels=int((normalized["label"] == "").sum()),
        label_counts={label: int(label_counts.get(label, 0)) for label in TRAINING_LABELS},
        min_length=int(content_lengths.min()) if len(normalized) else 0,
        max_length=int(content_lengths.max()) if len(normalized) else 0,
        average_length=round(float(content_lengths.mean()), 2) if len(normalized) else 0.0,
        short_contents=int((content_lengths < min_content_length).sum()),
        long_contents=int((content_lengths > max_content_length).sum()),
    )


def validate_training_dataframe(
    dataframe: pd.DataFrame,
    file_path: str | Path = "<dataframe>",
    *,
    require_all_labels: bool = True,
    min_samples_per_label: int = 1,
    min_content_length: int = 5,
    max_content_length: int | None = None,
) -> DatasetSummary:
    """校验训练数据是否满足三分类微调要求。"""
    normalized = normalize_training_dataframe(dataframe)
    summary = build_dataset_summary(
        normalized,
        file_path=file_path,
        min_content_length=min_content_length,
        max_content_length=max_content_length or 500,
    )

    problems: list[str] = []
    if summary.total_rows == 0:
        problems.append("训练数据为空")

    if summary.empty_contents:
        problems.append(f"存在 {summary.empty_contents} 条空文本")

    if summary.missing_labels:
        problems.append(f"存在 {summary.missing_labels} 条缺失标签")

    if summary.duplicate_contents:
        problems.append(f"存在 {summary.duplicate_contents} 条重复文本")

    if summary.short_contents:
        problems.append(
            f"存在 {summary.short_contents} 条过短文本(<{min_content_length} 字)"
        )

    if max_content_length is not None and summary.long_contents:
        problems.append(
            f"存在 {summary.long_contents} 条过长文本(>{max_content_length} 字)"
        )

    observed_labels = set(label for label in normalized["label"] if label)
    extra_labels = sorted(observed_labels - set(TRAINING_LABELS))
    if extra_labels:
        problems.append(f"发现非法标签: {', '.join(extra_labels)}")

    missing_required_labels = [
        label for label in TRAINING_LABELS if summary.label_counts.get(label, 0) == 0
    ]
    if require_all_labels and missing_required_labels:
        problems.append(f"缺少必要标签: {', '.join(missing_required_labels)}")

    for label in TRAINING_LABELS:
        count = summary.label_counts.get(label, 0)
        if count and count < min_samples_per_label:
            problems.append(
                f"标签 {label} 样本不足: {count} < {min_samples_per_label}"
            )

    if problems:
        raise DatasetValidationError(
            f"{file_path} 校验失败: " + "；".join(problems)
        )

    return summary


def load_labeled_texts(
    file_path: str | Path,
    *,
    require_all_labels: bool = True,
    min_samples_per_label: int = 1,
    min_content_length: int = 5,
    max_content_length: int | None = None,
) -> tuple[list[str], list[int], DatasetSummary]:
    """读取并校验训练数据，返回文本、数字标签和摘要。"""
    dataframe = read_training_csv(file_path)
    summary = validate_training_dataframe(
        dataframe,
        file_path=file_path,
        require_all_labels=require_all_labels,
        min_samples_per_label=min_samples_per_label,
        min_content_length=min_content_length,
        max_content_length=max_content_length,
    )
    texts = dataframe["content"].tolist()
    labels = [LABEL_TO_ID[label] for label in dataframe["label"].tolist()]
    return texts, labels, summary
