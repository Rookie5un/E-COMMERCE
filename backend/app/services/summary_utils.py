"""
分析结果摘要工具。
"""

from __future__ import annotations

from typing import Iterable

SENTIMENT_ORDER = ("positive", "neutral", "negative")


def build_sentiment_distribution(rows: Iterable[tuple]) -> tuple[dict[str, dict[str, float]], int]:
    """将数据库统计结果规范化为前端统一使用的结构。"""
    distribution = {
        label: {
            "count": 0,
            "avg_confidence": 0.0,
            "percentage": 0.0,
        }
        for label in SENTIMENT_ORDER
    }

    total_reviews = 0
    for row in rows:
        label = row[0]
        count = int(row[1])
        avg_confidence = float(row[2]) if len(row) > 2 and row[2] is not None else 0.0

        if label not in distribution:
            continue

        distribution[label]["count"] = count
        distribution[label]["avg_confidence"] = avg_confidence
        total_reviews += count

    if total_reviews:
        for label in SENTIMENT_ORDER:
            distribution[label]["percentage"] = round(
                distribution[label]["count"] / total_reviews * 100,
                2,
            )

    return distribution, total_reviews
