"""
情感模型解析工具。

优先使用本地三分类模型目录，目录不存在时再回退到显式路径或 Hugging Face 名称。
"""

from __future__ import annotations

from pathlib import Path

LOCAL_MODEL_ALIASES = {"roberta-sentiment"}


def resolve_sentiment_model_path(
    *,
    model_name: str | None,
    model_folder: str | None,
    fallback_model_name: str | None,
    explicit_model_path: str | None = None,
) -> str:
    """解析情感分析模型路径。"""
    candidate_names = [explicit_model_path, model_name, fallback_model_name]
    model_root = Path(model_folder).expanduser() if model_folder else None
    remote_fallbacks: list[str] = []

    for candidate in candidate_names:
        if not candidate:
            continue

        candidate_path = Path(candidate).expanduser()
        if candidate_path.exists():
            return str(candidate_path)

        if model_root is not None:
            local_alias_path = model_root / candidate
            if local_alias_path.exists():
                return str(local_alias_path)

        if candidate not in LOCAL_MODEL_ALIASES:
            remote_fallbacks.append(candidate)

    if remote_fallbacks:
        return remote_fallbacks[0]

    raise ValueError("未提供可用的情感模型路径或模型名")
