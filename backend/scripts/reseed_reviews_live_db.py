#!/usr/bin/env python3
"""
保留 users，清空其余业务数据，并重灌 300 条评论数据（一次性脚本）。

说明：
1) 严格读取真实数据库结构，不依赖项目建表 SQL。
2) 仅保留 users，其余表全量清空并重建 products/review_batches/reviews。
3) 评论来源：仓库根目录 online_shopping_10_cats.csv，固定随机种子保证可复现。
"""

from __future__ import annotations

import csv
import hashlib
import os
import random
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Sequence
from urllib.parse import unquote, urlparse

import pymysql


EXPECTED_TABLES = {
    "users",
    "products",
    "review_batches",
    "reviews",
    "analysis_runs",
    "review_sentiments",
    "aspect_mentions",
    "issue_topics",
    "issue_topic_reviews",
    "reports",
}

TRUNCATE_ORDER = [
    "issue_topic_reviews",
    "issue_topics",
    "aspect_mentions",
    "review_sentiments",
    "reports",
    "analysis_runs",
    "reviews",
    "review_batches",
    "products",
]

PRODUCT_PLAN = [
    {
        "cat": "手机",
        "name": "旗舰手机A",
        "category": "手机数码",
        "platform": "京东",
        "reviews": 90,
    },
    {
        "cat": "平板",
        "name": "平板设备B",
        "category": "电脑办公",
        "platform": "天猫",
        "reviews": 70,
    },
    {
        "cat": "计算机",
        "name": "轻薄本C",
        "category": "电脑办公",
        "platform": "京东",
        "reviews": 70,
    },
    {
        "cat": "洗发水",
        "name": "洗护套装D",
        "category": "美妆个护",
        "platform": "淘宝",
        "reviews": 70,
    },
]

CAT_SLUG = {
    "手机": "phone",
    "平板": "tablet",
    "计算机": "computer",
    "洗发水": "shampoo",
}

RANDOM_SEED = 20260416


@dataclass(frozen=True)
class DBConfig:
    host: str
    port: int
    user: str
    password: str
    database: str
    unix_socket: str | None = None


def load_env_file(env_path: Path) -> None:
    """轻量解析 .env 并写入环境变量（不覆盖已有变量）。"""
    if not env_path.exists():
        return

    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :]
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


def parse_database_url(database_url: str) -> DBConfig:
    """解析 mysql+pymysql://user:pass@host:port/db。"""
    parsed = urlparse(database_url)
    if parsed.scheme not in {"mysql+pymysql", "mysql"}:
        raise ValueError(f"仅支持 MySQL DATABASE_URL，当前 scheme={parsed.scheme}")
    if not parsed.path or parsed.path == "/":
        raise ValueError("DATABASE_URL 缺少数据库名")

    socket_path = "/tmp/mysql.sock" if Path("/tmp/mysql.sock").exists() else None
    return DBConfig(
        host=parsed.hostname or "127.0.0.1",
        port=parsed.port or 3306,
        user=unquote(parsed.username or ""),
        password=unquote(parsed.password or ""),
        database=parsed.path.lstrip("/"),
        unix_socket=socket_path,
    )


def connect_db(cfg: DBConfig):
    kwargs = {
        "user": cfg.user,
        "password": cfg.password,
        "database": cfg.database,
        "charset": "utf8mb4",
        "autocommit": False,
        "cursorclass": pymysql.cursors.DictCursor,
    }
    if cfg.unix_socket:
        kwargs["unix_socket"] = cfg.unix_socket
    else:
        kwargs["host"] = cfg.host
        kwargs["port"] = cfg.port
    return pymysql.connect(**kwargs)


def clean_text(text: str) -> str:
    """与 backend/app/nlp/text_processor.py 保持一致。"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(
        r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
        "",
        text,
    )
    text = re.sub(r"[^\u4e00-\u9fa5a-zA-Z0-9\s,.!?，。！？、]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def read_source_pool(dataset_path: Path) -> Dict[str, Dict[str, List[dict]]]:
    """
    读取评论源数据，按 cat/label 分组，并按 cleaned_content 去重。
    label: '1' 正向，'0' 负向。
    """
    pool: Dict[str, Dict[str, List[dict]]] = {}
    dedupe: Dict[str, Dict[str, set]] = {}

    cats_needed = {plan["cat"] for plan in PRODUCT_PLAN}
    for cat in cats_needed:
        pool[cat] = {"1": [], "0": []}
        dedupe[cat] = {"1": set(), "0": set()}

    with dataset_path.open("r", encoding="utf-8-sig", newline="") as fp:
        reader = csv.DictReader(fp)
        for row in reader:
            cat = (row.get("cat") or "").strip()
            label = str(row.get("label") or "").strip()
            raw_content = (row.get("review") or "").strip()
            if cat not in pool or label not in {"0", "1"}:
                continue
            cleaned = clean_text(raw_content)
            if len(cleaned) < 5:
                continue
            digest = sha256_hex(cleaned)
            if digest in dedupe[cat][label]:
                continue
            dedupe[cat][label].add(digest)
            pool[cat][label].append(
                {
                    "cat": cat,
                    "label": label,
                    "raw_content": raw_content,
                    "cleaned_content": cleaned,
                    "content_hash": digest,
                }
            )
    return pool


def choose_candidates(
    grouped: Dict[str, List[dict]],
    total: int,
    used_hashes: set,
    rng: random.Random,
) -> List[dict]:
    """在正负标签覆盖下抽样 total 条，且全局 content_hash 唯一。"""
    target_pos = total // 2
    target_neg = total - target_pos

    pos_avail = [x for x in grouped["1"] if x["content_hash"] not in used_hashes]
    neg_avail = [x for x in grouped["0"] if x["content_hash"] not in used_hashes]

    pos_take = min(target_pos, len(pos_avail))
    neg_take = min(target_neg, len(neg_avail))

    selected = []
    if pos_take:
        selected.extend(rng.sample(pos_avail, pos_take))
    if neg_take:
        selected.extend(rng.sample(neg_avail, neg_take))

    for item in selected:
        used_hashes.add(item["content_hash"])

    remaining = total - len(selected)
    if remaining > 0:
        fallback = [
            x
            for x in grouped["1"] + grouped["0"]
            if x["content_hash"] not in used_hashes
        ]
        if len(fallback) < remaining:
            raise RuntimeError(
                f"可用样本不足：需要补充 {remaining} 条，但只剩 {len(fallback)} 条"
            )
        extra = rng.sample(fallback, remaining)
        selected.extend(extra)
        for item in extra:
            used_hashes.add(item["content_hash"])

    rng.shuffle(selected)
    return selected


def rating_by_label(label: str, rng: random.Random) -> int:
    if label == "1":
        return rng.choice([4, 4, 5, 5, 5])
    return rng.choice([1, 1, 2, 2, 3])


def random_review_time(now: datetime, rng: random.Random) -> datetime:
    days = rng.randint(0, 179)
    seconds = rng.randint(0, 86399)
    return now - timedelta(days=days, seconds=seconds)


def fetch_row_counts(cursor) -> Dict[str, int]:
    sql = (
        "SELECT 'users' AS table_name, COUNT(*) AS rows_count FROM users "
        "UNION ALL SELECT 'products', COUNT(*) FROM products "
        "UNION ALL SELECT 'review_batches', COUNT(*) FROM review_batches "
        "UNION ALL SELECT 'reviews', COUNT(*) FROM reviews "
        "UNION ALL SELECT 'analysis_runs', COUNT(*) FROM analysis_runs "
        "UNION ALL SELECT 'review_sentiments', COUNT(*) FROM review_sentiments "
        "UNION ALL SELECT 'aspect_mentions', COUNT(*) FROM aspect_mentions "
        "UNION ALL SELECT 'issue_topics', COUNT(*) FROM issue_topics "
        "UNION ALL SELECT 'issue_topic_reviews', COUNT(*) FROM issue_topic_reviews "
        "UNION ALL SELECT 'reports', COUNT(*) FROM reports"
    )
    cursor.execute(sql)
    return {row["table_name"]: int(row["rows_count"]) for row in cursor.fetchall()}


def assert_live_schema(cursor) -> None:
    cursor.execute("SHOW TABLES")
    tables = {next(iter(row.values())) for row in cursor.fetchall()}
    missing = EXPECTED_TABLES - tables
    if missing:
        raise RuntimeError(f"实时数据库缺少表: {sorted(missing)}")


def select_created_by_user(cursor) -> tuple[int, List[dict]]:
    cursor.execute(
        "SELECT id, username, role, status, email, created_at FROM users ORDER BY id"
    )
    users = cursor.fetchall()
    if not users:
        raise RuntimeError("users 表为空，无法执行重灌（必须保留至少一个用户）")
    admin = next((u for u in users if u["role"] == "admin"), None)
    chosen = admin["id"] if admin else users[0]["id"]
    return chosen, users


def truncate_non_user_tables(cursor) -> None:
    cursor.execute("SET FOREIGN_KEY_CHECKS=0")
    try:
        for table in TRUNCATE_ORDER:
            cursor.execute(f"TRUNCATE TABLE `{table}`")
    finally:
        cursor.execute("SET FOREIGN_KEY_CHECKS=1")


def reseed_business_data(cursor, created_by: int, dataset_path: Path) -> None:
    rng = random.Random(RANDOM_SEED)
    pool = read_source_pool(dataset_path)
    now = datetime.utcnow()
    used_hashes = set()

    for plan in PRODUCT_PLAN:
        cat = plan["cat"]
        samples = choose_candidates(pool[cat], plan["reviews"], used_hashes, rng)

        cursor.execute(
            """
            INSERT INTO products
              (name, category, platform, url, description, created_by)
            VALUES
              (%s, %s, %s, %s, %s, %s)
            """,
            (
                plan["name"],
                plan["category"],
                plan["platform"],
                f"https://example.com/{CAT_SLUG[cat]}",
                f"重灌脚本导入的{cat}评论样本集",
                created_by,
            ),
        )
        product_id = cursor.lastrowid

        cursor.execute(
            """
            INSERT INTO review_batches
              (product_id, source_type, file_name, row_count, imported_count,
               duplicate_count, failed_count, status, created_by, finished_at)
            VALUES
              (%s, 'csv_import', %s, 0, 0, 0, 0, 'completed', %s, %s)
            """,
            (product_id, f"{CAT_SLUG[cat]}_seed_20260416.csv", created_by, now),
        )
        batch_id = cursor.lastrowid

        row_count = len(samples)
        imported_count = 0
        duplicate_count = 0
        failed_count = 0

        for idx, sample in enumerate(samples, start=1):
            cleaned = sample["cleaned_content"]
            if not cleaned:
                failed_count += 1
                continue

            rating = rating_by_label(sample["label"], rng)
            review_time = random_review_time(now, rng)
            external_id = f"{CAT_SLUG[cat]}-{idx:04d}"

            cursor.execute(
                """
                INSERT INTO reviews
                  (product_id, batch_id, external_id, raw_content, cleaned_content,
                   content_hash, rating, review_time, is_valid, duplicate_of)
                VALUES
                  (%s, %s, %s, %s, %s, %s, %s, %s, 1, NULL)
                """,
                (
                    product_id,
                    batch_id,
                    external_id,
                    sample["raw_content"],
                    cleaned,
                    sample["content_hash"],
                    rating,
                    review_time,
                ),
            )
            imported_count += 1

        cursor.execute(
            """
            UPDATE review_batches
            SET row_count=%s,
                imported_count=%s,
                duplicate_count=%s,
                failed_count=%s,
                status='completed',
                finished_at=%s
            WHERE id=%s
            """,
            (
                row_count,
                imported_count,
                duplicate_count,
                failed_count,
                now,
                batch_id,
            ),
        )


def run_quality_checks(cursor, users_before: Sequence[dict]) -> None:
    # 用户保留校验
    cursor.execute(
        "SELECT id, username, role, status, email, created_at FROM users ORDER BY id"
    )
    users_after = cursor.fetchall()
    if list(users_before) != list(users_after):
        raise RuntimeError("users 表发生变化，未满足“仅保留用户信息”要求")

    # 行数校验
    counts = fetch_row_counts(cursor)
    expected = {
        "products": 4,
        "review_batches": 4,
        "reviews": 300,
        "analysis_runs": 0,
        "review_sentiments": 0,
        "aspect_mentions": 0,
        "issue_topics": 0,
        "issue_topic_reviews": 0,
        "reports": 0,
    }
    for table, value in expected.items():
        if counts.get(table) != value:
            raise RuntimeError(
                f"{table} 行数不符合预期：实际 {counts.get(table)}, 预期 {value}"
            )

    # 内容哈希唯一
    cursor.execute(
        "SELECT COUNT(*) AS c, COUNT(DISTINCT content_hash) AS d FROM reviews"
    )
    hash_stat = cursor.fetchone()
    if int(hash_stat["c"]) != int(hash_stat["d"]):
        raise RuntimeError("reviews.content_hash 存在重复，违反唯一性预期")

    # 抽查 20 条质量
    cursor.execute(
        "SELECT id, cleaned_content, content_hash, rating FROM reviews ORDER BY RAND() LIMIT 20"
    )
    for row in cursor.fetchall():
        cleaned = (row["cleaned_content"] or "").strip()
        if not cleaned:
            raise RuntimeError(f"评论 {row['id']} cleaned_content 为空")
        if not row["content_hash"] or len(row["content_hash"]) != 64:
            raise RuntimeError(f"评论 {row['id']} content_hash 非法")
        if row["rating"] is None or not (1 <= int(row["rating"]) <= 5):
            raise RuntimeError(f"评论 {row['id']} rating 越界")


def main() -> int:
    repo_root = Path(__file__).resolve().parents[2]
    backend_dir = repo_root / "backend"
    env_file = backend_dir / ".env"
    dataset_file = repo_root / "online_shopping_10_cats.csv"

    load_env_file(env_file)
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("ERROR: 未读取到 DATABASE_URL（请检查 backend/.env）", file=sys.stderr)
        return 1
    if not dataset_file.exists():
        print(f"ERROR: 评论源文件不存在: {dataset_file}", file=sys.stderr)
        return 1

    cfg = parse_database_url(database_url)
    print(f"[INFO] Target DB: {cfg.database}")
    print(f"[INFO] Source CSV: {dataset_file}")
    print(f"[INFO] Random seed: {RANDOM_SEED}")

    conn = connect_db(cfg)
    try:
        with conn.cursor() as cursor:
            assert_live_schema(cursor)
            created_by, users_before = select_created_by_user(cursor)
            print(f"[INFO] created_by user id: {created_by}")
            print(f"[INFO] users count: {len(users_before)}")
            before_counts = fetch_row_counts(cursor)
            print(f"[INFO] before counts: {before_counts}")

            truncate_non_user_tables(cursor)
            reseed_business_data(cursor, created_by, dataset_file)
            run_quality_checks(cursor, users_before)

        conn.commit()
        with conn.cursor() as cursor:
            after_counts = fetch_row_counts(cursor)
        print(f"[INFO] after counts: {after_counts}")
        print("[DONE] Reseed completed successfully.")
        return 0
    except Exception as exc:
        conn.rollback()
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())

