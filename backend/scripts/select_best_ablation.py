#!/usr/bin/env python3
"""
Select the best ablation group from a summary CSV.

Ranking rule:
1. macro_f1_mean desc
2. accuracy_mean desc
3. macro_f1_std asc

Usage:
  python scripts/select_best_ablation.py \
    --summary_csv data/experiments/thesis_core/summary/ablation_group_summary.csv
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Select the best ablation group")
    parser.add_argument("--summary_csv", required=True, help="Path to ablation_group_summary.csv")
    parser.add_argument(
        "--print_table",
        action="store_true",
        help="Print all ranked groups before the winner",
    )
    args = parser.parse_args()

    summary_csv = Path(args.summary_csv).resolve()
    if not summary_csv.exists():
        raise FileNotFoundError(f"summary csv not found: {summary_csv}")

    rows: list[dict[str, str]] = []
    with summary_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

    if not rows:
        raise RuntimeError(f"no rows found in summary csv: {summary_csv}")

    ranked = sorted(
        rows,
        key=lambda row: (
            -float(row["macro_f1_mean"]),
            -float(row["accuracy_mean"]),
            float(row["macro_f1_std"]),
        ),
    )

    if args.print_table:
        for row in ranked:
            print(
                f'{row["group"]},'
                f' macro_f1_mean={float(row["macro_f1_mean"]):.6f},'
                f' accuracy_mean={float(row["accuracy_mean"]):.6f},'
                f' macro_f1_std={float(row["macro_f1_std"]):.6f}'
            )

    print(ranked[0]["group"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
