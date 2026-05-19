#!/usr/bin/env python3
"""
Collect ablation results from training_summary.json files, export CSVs,
and optionally draw bar charts if matplotlib is available.

Usage:
  python scripts/collect_ablation_results.py \
    --run_root data/experiments/ablation_20260421_120000
"""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean, stdev
from typing import Dict, List


@dataclass
class RunRecord:
    group: str
    seed: str
    accuracy: float
    macro_f1: float
    train_file: str
    model_name: str
    epochs: int
    batch_size: int
    learning_rate: float
    max_length: int
    use_fgm: bool
    use_class_weight: bool
    early_stopping: bool
    loss_type: str


def parse_seed_from_path(path: Path) -> str:
    # expected: .../<group>/seed_<seed>/training_summary.json
    seed_dir = path.parent.name
    if seed_dir.startswith("seed_"):
        return seed_dir[len("seed_"):]
    return seed_dir


def load_run_records(run_root: Path) -> List[RunRecord]:
    records: List[RunRecord] = []
    for summary_path in sorted(run_root.glob("*/seed_*/training_summary.json")):
        group = summary_path.parent.parent.name
        seed = parse_seed_from_path(summary_path)

        data = json.loads(summary_path.read_text(encoding="utf-8"))
        metrics = data.get("best_metrics", {})
        cfg = data.get("training_config", {})

        record = RunRecord(
            group=group,
            seed=seed,
            accuracy=float(metrics.get("accuracy", 0.0)),
            macro_f1=float(metrics.get("f1_score", 0.0)),
            train_file=str(cfg.get("train_file", "")),
            model_name=str(cfg.get("model_name", "")),
            epochs=int(cfg.get("epochs", 0)),
            batch_size=int(cfg.get("batch_size", 0)),
            learning_rate=float(cfg.get("learning_rate", 0.0)),
            max_length=int(cfg.get("max_length", 0)),
            use_fgm=bool(cfg.get("use_fgm", False)),
            use_class_weight=bool(cfg.get("use_class_weight", False)),
            early_stopping=bool(cfg.get("early_stopping", False)),
            loss_type=str(cfg.get("loss_type", "")),
        )
        records.append(record)
    return records


def write_raw_csv(records: List[RunRecord], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "group",
            "seed",
            "accuracy",
            "macro_f1",
            "train_file",
            "model_name",
            "epochs",
            "batch_size",
            "learning_rate",
            "max_length",
            "use_fgm",
            "use_class_weight",
            "early_stopping",
            "loss_type",
        ])
        for r in records:
            writer.writerow([
                r.group,
                r.seed,
                f"{r.accuracy:.6f}",
                f"{r.macro_f1:.6f}",
                r.train_file,
                r.model_name,
                r.epochs,
                r.batch_size,
                r.learning_rate,
                r.max_length,
                int(r.use_fgm),
                int(r.use_class_weight),
                int(r.early_stopping),
                r.loss_type,
            ])


def group_stats(records: List[RunRecord]) -> List[Dict[str, str]]:
    grouped: Dict[str, List[RunRecord]] = {}
    for r in records:
        grouped.setdefault(r.group, []).append(r)

    stats_rows: List[Dict[str, str]] = []
    for group in sorted(grouped.keys()):
        rows = grouped[group]
        acc_list = [r.accuracy for r in rows]
        f1_list = [r.macro_f1 for r in rows]

        acc_mean = mean(acc_list)
        f1_mean = mean(f1_list)
        acc_std = stdev(acc_list) if len(acc_list) > 1 else 0.0
        f1_std = stdev(f1_list) if len(f1_list) > 1 else 0.0

        stats_rows.append(
            {
                "group": group,
                "n_runs": str(len(rows)),
                "accuracy_mean": f"{acc_mean:.6f}",
                "accuracy_std": f"{acc_std:.6f}",
                "macro_f1_mean": f"{f1_mean:.6f}",
                "macro_f1_std": f"{f1_std:.6f}",
            }
        )

    return stats_rows


def write_summary_csv(summary_rows: List[Dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "group",
                "n_runs",
                "accuracy_mean",
                "accuracy_std",
                "macro_f1_mean",
                "macro_f1_std",
            ],
        )
        writer.writeheader()
        for row in summary_rows:
            writer.writerow(row)


def write_markdown_table(summary_rows: List[Dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "| group | n_runs | accuracy_mean | accuracy_std | macro_f1_mean | macro_f1_std |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for row in summary_rows:
        lines.append(
            "| {group} | {n_runs} | {accuracy_mean} | {accuracy_std} | {macro_f1_mean} | {macro_f1_std} |".format(**row)
        )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def try_plot(summary_rows: List[Dict[str, str]], out_dir: Path) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("[INFO] matplotlib unavailable, skip plotting.")
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    groups = [r["group"] for r in summary_rows]
    acc_mean = [float(r["accuracy_mean"]) for r in summary_rows]
    acc_std = [float(r["accuracy_std"]) for r in summary_rows]
    f1_mean = [float(r["macro_f1_mean"]) for r in summary_rows]
    f1_std = [float(r["macro_f1_std"]) for r in summary_rows]

    # Accuracy
    plt.figure(figsize=(10, 5))
    plt.bar(groups, acc_mean, yerr=acc_std, capsize=4)
    plt.title("Ablation Accuracy (mean ± std)")
    plt.ylabel("Accuracy")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(out_dir / "ablation_accuracy.png", dpi=200)
    plt.close()

    # Macro-F1
    plt.figure(figsize=(10, 5))
    plt.bar(groups, f1_mean, yerr=f1_std, capsize=4)
    plt.title("Ablation Macro-F1 (mean ± std)")
    plt.ylabel("Macro-F1")
    plt.xticks(rotation=20, ha="right")
    plt.tight_layout()
    plt.savefig(out_dir / "ablation_macro_f1.png", dpi=200)
    plt.close()

    print(f"[OK] plots saved: {out_dir}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect and summarize ablation experiment results")
    parser.add_argument("--run_root", required=True, help="experiment root dir, e.g. data/experiments/ablation_xxx")
    parser.add_argument("--output_dir", default=None, help="output dir (default: <run_root>/summary)")
    parser.add_argument("--no_plot", action="store_true", help="disable plotting")
    args = parser.parse_args()

    run_root = Path(args.run_root).resolve()
    if not run_root.exists():
        raise FileNotFoundError(f"run_root not found: {run_root}")

    output_dir = Path(args.output_dir).resolve() if args.output_dir else run_root / "summary"

    records = load_run_records(run_root)
    if not records:
        raise RuntimeError(f"No training_summary.json found under {run_root}")

    raw_csv = output_dir / "ablation_raw_runs.csv"
    summary_csv = output_dir / "ablation_group_summary.csv"
    summary_md = output_dir / "ablation_group_summary.md"

    write_raw_csv(records, raw_csv)
    summary_rows = group_stats(records)
    write_summary_csv(summary_rows, summary_csv)
    write_markdown_table(summary_rows, summary_md)

    if not args.no_plot:
        try_plot(summary_rows, output_dir)

    print("[OK] collection finished")
    print(f"[OK] raw csv    : {raw_csv}")
    print(f"[OK] summary csv: {summary_csv}")
    print(f"[OK] summary md : {summary_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
