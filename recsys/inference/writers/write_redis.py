"""推荐结果写回 Redis 入口。"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pymysql
import redis

try:
    from runtime_paths import detect_workspace_root, resolve_workspace_path
except ModuleNotFoundError as exc:
    if __name__ == "__main__":
        raise RuntimeError(
            "未找到依赖。请在 recsys 目录执行："
            "uv run python inference/writers/write_redis.py"
        ) from exc
    raise


WORKSPACE_ROOT = detect_workspace_root(anchor_file=Path(__file__).resolve())


@dataclass(slots=True)
class RedisWritebackSummary:
    total_rows: int
    rows_with_items: int
    mapped_users: int
    written_keys: int
    skipped_empty_items: int
    skipped_no_user_mapping: int
    skipped_invalid_rows: int
    failed_writes: int
    strategy: str
    report_path: str


def _load_env_file(env_file: Path) -> None:
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
    return redis.Redis(
        host=_require_env("REDIS_HOST"),
        port=int(_require_env("REDIS_PORT")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
    )


def _build_payload(
    *,
    row: dict[str, Any],
    generated_at: str,
    strategy: str,
    max_items: int,
) -> str:
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
                "reason": str(item.get("reason") or strategy),
            }
        )

    payload = {
        "strategy": strategy,
        "generated_at": generated_at,
        "items": normalized_items,
    }
    return json.dumps(payload, ensure_ascii=False)


def write_ranked_to_redis(
    *,
    strategy: str,
    ranked_jsonl: Path,
    report_json: Path,
    env_file: Path,
    max_items: int = 100,
    batch_size: int = 500,
    dry_run: bool = False,
) -> RedisWritebackSummary:
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
    total_rows = rows_with_items = mapped_users = written_keys = 0
    skipped_empty_items = skipped_no_user_mapping = skipped_invalid_rows = (
        failed_writes
    ) = 0
    pending: list[tuple[str, str]] = []

    def flush_pending() -> None:
        nonlocal pending, written_keys, failed_writes
        if not pending or dry_run or redis_client is None:
            pending = []
            return

        pipeline = redis_client.pipeline(transaction=False)
        for key, payload_text in pending:
            pipeline.set(key, payload_text)

        try:
            pipeline.execute()
            written_keys += len(pending)
        except Exception:
            for key, payload_text in pending:
                try:
                    redis_client.set(key, payload_text)
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
                # 容错：处理 user_key 实际是整形 id，但 type 被误标为 msno 的情况
                if user_key.isdigit():
                    user_id = int(user_key)
                else:
                    skipped_no_user_mapping += 1
                    continue
            else:
                user_id = mapped

        mapped_users += 1
        redis_key = f"rec:user:{user_id}:strategy:{strategy}"
        payload_text = _build_payload(
            row=row,
            generated_at=generated_at,
            strategy=strategy,
            max_items=max_items,
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
            "strategy": strategy,
            "max_items": max_items,
            "batch_size": batch_size,
            "dry_run": dry_run,
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
        json.dumps(report_content, ensure_ascii=False, indent=2), encoding="utf-8"
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
        strategy=strategy,
        report_path=str(report_json),
    )


def _default_paths(strategy: str) -> tuple[Path, Path, Path]:
    artifacts_root = WORKSPACE_ROOT / "recsys" / "artifacts"
    if strategy == "two_tower":
        # 加上 server_local 目录
        ranked_jsonl = (
            artifacts_root
            / "two_tower"
            / "server_local"
            / "ranked"
            / "user_topk_scored.jsonl"
        )
        report_json = (
            artifacts_root
            / "two_tower"
            / "server_local"
            / "reports"
            / "redis_write_report.json"
        )
    else:
        ranked_jsonl = (
            artifacts_root / "content_based" / "ranked" / "user_topk_scored.jsonl"
        )
        report_json = (
            artifacts_root / "content_based" / "reports" / "redis_write_report.json"
        )
    return ranked_jsonl, report_json, WORKSPACE_ROOT / ".env"


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="将推荐 ranked 结果写入 Redis。")
    parser.add_argument(
        "--strategy",
        choices=["content_based", "two_tower"],
        default="content_based",
        help="写回策略类型，用于生成对应 Redis Key 及推导默认路径。",
    )
    parser.add_argument("--ranked-jsonl", help="ranked 输入文件路径。")
    parser.add_argument("--report-json", help="写回报告输出路径。")
    parser.add_argument("--env-file", help="环境变量文件路径。")
    parser.add_argument("--max-items", type=int, default=100)
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--allow-external-paths", action="store_true")
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    default_ranked_jsonl, default_report_json, default_env_file = _default_paths(
        args.strategy
    )
    allow_ext = bool(args.allow_external_paths)

    ranked_jsonl = resolve_workspace_path(
        str(args.ranked_jsonl or default_ranked_jsonl),
        workspace_root=WORKSPACE_ROOT,
        allow_external_paths=allow_ext,
    )
    report_json = resolve_workspace_path(
        str(args.report_json or default_report_json),
        workspace_root=WORKSPACE_ROOT,
        allow_external_paths=allow_ext,
    )
    env_file = resolve_workspace_path(
        str(args.env_file or default_env_file),
        workspace_root=WORKSPACE_ROOT,
        allow_external_paths=allow_ext,
    )

    summary = write_ranked_to_redis(
        strategy=args.strategy,
        ranked_jsonl=ranked_jsonl,
        report_json=report_json,
        env_file=env_file,
        max_items=args.max_items,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
    )
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
