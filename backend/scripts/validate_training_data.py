#!/usr/bin/env python3
"""
训练数据校验脚本。

示例:
python scripts/validate_training_data.py \
  --train_file data/train_multiclass.csv \
  --require_all_labels \
  --min_samples_per_label 500
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = CURRENT_DIR.parent
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from training_data_utils import (  # noqa: E402
    DatasetValidationError,
    build_dataset_summary,
    read_training_csv,
    validate_training_dataframe,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验三分类训练数据")
    parser.add_argument("--train_file", required=True, help="训练数据 CSV 路径")
    parser.add_argument(
        "--require_all_labels",
        action="store_true",
        help="要求数据集中同时包含 negative / neutral / positive",
    )
    parser.add_argument(
        "--min_samples_per_label",
        type=int,
        default=1,
        help="每个标签的最小样本数",
    )
    parser.add_argument(
        "--min_content_length",
        type=int,
        default=5,
        help="最短文本长度阈值",
    )
    parser.add_argument(
        "--max_content_length",
        type=int,
        default=500,
        help="最长文本长度阈值",
    )
    parser.add_argument(
        "--output_json",
        help="可选，输出校验摘要 JSON 文件",
    )
    args = parser.parse_args()

    dataframe = read_training_csv(args.train_file)
    summary = build_dataset_summary(
        dataframe,
        file_path=args.train_file,
        min_content_length=args.min_content_length,
        max_content_length=args.max_content_length,
    )

    print("=" * 60)
    print("训练数据校验报告")
    print("=" * 60)
    print(json.dumps(summary.to_dict(), ensure_ascii=False, indent=2))

    try:
        validate_training_dataframe(
            dataframe,
            file_path=args.train_file,
            require_all_labels=args.require_all_labels,
            min_samples_per_label=args.min_samples_per_label,
            min_content_length=args.min_content_length,
            max_content_length=args.max_content_length,
        )
        print("\n✅ 校验通过")
    except DatasetValidationError as exc:
        print(f"\n❌ 校验失败: {exc}")
        if args.output_json:
            output_path = Path(args.output_json)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        return 1

    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
