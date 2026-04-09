"""P5：将 content_based 排序结果写回 Redis。"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymysql
import redis


@dataclass(slots=True)
class RedisWritebackSummary:
    """Redis 写回摘要。"""

    total_rows: int
    rows_with_items: int
    mapped_users: int
    written_keys: int
    skipped_empty_items: int
    skipped_no_user_mapping: int
    skipped_invalid_rows: int
    failed_writes: int
    key_version: int
    ttl_seconds: int
    report_path: str


def _load_env_file(env_file: Path) -> None:
    """读取 .env 并补齐环境变量（已存在变量不覆盖）。"""
    if not env_file.exists():
        return

    for line in env_file.read_text(encoding="utf-8").splitlines():
        text = line.strip()
        if not text or text.startswith("#") or "=" not in text:
            continue
        key, raw_value = text.split("=", 1)
        key = key.strip()
        value = raw_value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _require_env(var_name: str) -> str:
    value = os.getenv(var_name)
    if value is None or value == "":
        raise RuntimeError(f"缺少环境变量: {var_name}")
    return value


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            yield json.loads(text)


def _load_user_id_map() -> dict[str, int]:
    """从 MySQL 加载 msno -> user_id 映射。"""
    connection = pymysql.connect(
        host=_require_env("MYSQL_HOST"),
        port=int(_require_env("MYSQL_PORT")),
        user=_require_env("MYSQL_USER"),
        password=_require_env("MYSQL_PASSWORD"),
        database=_require_env("MYSQL_DATABASE"),
        charset="utf8mb4",
        autocommit=True,
    )

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT id, msno FROM users")
            rows = cursor.fetchall()
    finally:
        connection.close()

    return {str(msno): int(user_id) for user_id, msno in rows}


def _create_redis_client() -> redis.Redis:
    redis_password = os.getenv("REDIS_PASSWORD")
    return redis.Redis(
        host=_require_env("REDIS_HOST"),
        port=int(_require_env("REDIS_PORT")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=redis_password,
        decode_responses=True,
    )


def _build_payload(
    *,
    row: dict[str, Any],
    generated_at: str,
    key_version: int,
    max_items: int,
    strategy_override: str | None,
) -> str:
    """构建写入 Redis 的 payload。"""
    strategy = strategy_override or str(row.get("strategy") or "content_cold_start")
    items = row.get("items") or []
    if not isinstance(items, list):
        items = []

    normalized_items: list[dict[str, Any]] = []
    for item in items[:max_items]:
        song_id = str(item.get("song_id") or "").strip()
        if not song_id:
            continue
        normalized_items.append(
            {
                "song_id": song_id,
                "rank": int(item.get("rank") or 0),
                "score": float(item.get("score") or 0.0),
                "reason": str(item.get("reason") or "content_cold_start"),
            }
        )

    payload = {
        "strategy": strategy,
        "version": key_version,
        "generated_at": generated_at,
        "items": normalized_items,
    }
    return json.dumps(payload, ensure_ascii=False)


def write_content_based_ranked_to_redis(
    *,
    ranked_jsonl: Path,
    report_json: Path,
    env_file: Path,
    key_version: int = 1,
    ttl_seconds: int = 86_400,
    max_items: int = 100,
    batch_size: int = 500,
    dry_run: bool = False,
    strategy_override: str | None = None,
) -> RedisWritebackSummary:
    """将 P4 产物写入 Redis 并输出写回报告。"""
    if key_version <= 0:
        raise ValueError("key_version 必须大于 0")
    if ttl_seconds <= 0:
        raise ValueError("ttl_seconds 必须大于 0")
    if max_items <= 0:
        raise ValueError("max_items 必须大于 0")
    if batch_size <= 0:
        raise ValueError("batch_size 必须大于 0")

    _load_env_file(env_file)
    user_id_map = _load_user_id_map()

    redis_client: redis.Redis | None = None
    if not dry_run:
        redis_client = _create_redis_client()
        redis_client.ping()

    generated_at = datetime.now(timezone.utc).isoformat()

    total_rows = 0
    rows_with_items = 0
    mapped_users = 0
    written_keys = 0
    skipped_empty_items = 0
    skipped_no_user_mapping = 0
    skipped_invalid_rows = 0
    failed_writes = 0

    pending: list[tuple[str, str]] = []

    def flush_pending() -> None:
        nonlocal pending, written_keys, failed_writes
        if not pending or dry_run or redis_client is None:
            pending = []
            return

        pipeline = redis_client.pipeline(transaction=False)
        for key, payload_text in pending:
            pipeline.setex(key, ttl_seconds, payload_text)

        try:
            pipeline.execute()
            written_keys += len(pending)
            pending = []
            return
        except Exception:
            # 批量失败时回退到逐条写入，便于统计失败记录。
            pass

        for key, payload_text in pending:
            try:
                redis_client.setex(key, ttl_seconds, payload_text)
                written_keys += 1
            except Exception:
                failed_writes += 1
        pending = []

    for row in _iter_jsonl(ranked_jsonl):
        total_rows += 1

        user_key_type = str(row.get("user_key_type") or "").strip()
        user_key = str(row.get("user_key") or "").strip()
        items = row.get("items") or []
        if not isinstance(items, list):
            skipped_invalid_rows += 1
            continue

        if not items:
            skipped_empty_items += 1
            continue
        rows_with_items += 1

        if user_key_type == "id":
            try:
                user_id = int(user_key)
            except ValueError:
                skipped_invalid_rows += 1
                continue
        elif user_key_type == "msno":
            mapped = user_id_map.get(user_key)
            if mapped is None:
                skipped_no_user_mapping += 1
                continue
            user_id = mapped
        else:
            skipped_invalid_rows += 1
            continue

        mapped_users += 1
        redis_key = f"rec:user:{user_id}:v{key_version}"
        payload_text = _build_payload(
            row=row,
            generated_at=generated_at,
            key_version=key_version,
            max_items=max_items,
            strategy_override=strategy_override,
        )
        pending.append((redis_key, payload_text))

        if len(pending) >= batch_size:
            flush_pending()

    flush_pending()

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_content = {
        "generated_at": generated_at,
        "input": {"ranked_jsonl": str(ranked_jsonl)},
        "settings": {
            "key_version": key_version,
            "ttl_seconds": ttl_seconds,
            "max_items": max_items,
            "batch_size": batch_size,
            "dry_run": dry_run,
            "strategy_override": strategy_override,
        },
        "summary": {
            "total_rows": total_rows,
            "rows_with_items": rows_with_items,
            "mapped_users": mapped_users,
            "written_keys": written_keys,
            "skipped_empty_items": skipped_empty_items,
            "skipped_no_user_mapping": skipped_no_user_mapping,
            "skipped_invalid_rows": skipped_invalid_rows,
            "failed_writes": failed_writes,
        },
    }
    report_json.write_text(
        json.dumps(report_content, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return RedisWritebackSummary(
        total_rows=total_rows,
        rows_with_items=rows_with_items,
        mapped_users=mapped_users,
        written_keys=written_keys,
        skipped_empty_items=skipped_empty_items,
        skipped_no_user_mapping=skipped_no_user_mapping,
        skipped_invalid_rows=skipped_invalid_rows,
        failed_writes=failed_writes,
        key_version=key_version,
        ttl_seconds=ttl_seconds,
        report_path=str(report_json),
    )


def summary_to_json(summary: RedisWritebackSummary) -> str:
    """将写回摘要转为 JSON 文本。"""
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2)
