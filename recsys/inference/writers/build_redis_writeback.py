"""推荐结果写回 Redis 入口（content_based / two_tower）。"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
RECSYS_ROOT = CURRENT_FILE.parents[2]
WORKSPACE_ROOT = CURRENT_FILE.parents[3]

for path_candidate in (WORKSPACE_ROOT, RECSYS_ROOT):
    path_str = str(path_candidate)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def _default_paths(strategy: str) -> tuple[Path, Path, Path]:
    """按策略返回默认输入输出路径。"""
    project_root = Path(__file__).resolve().parents[3]
    artifacts_root = project_root / "recsys" / "artifacts"

    if strategy == "two_tower":
        ranked_jsonl = (
            artifacts_root / "two_tower" / "ranked" / "user_topk_scored.jsonl"
        )
        report_json = (
            artifacts_root / "two_tower" / "reports" / "two_tower_redis_report.json"
        )
    else:
        ranked_jsonl = (
            artifacts_root / "content_based" / "ranked" / "user_topk_scored.jsonl"
        )
        report_json = (
            artifacts_root / "content_based" / "reports" / "redis_write_report.json"
        )

    env_file = project_root / ".env"
    return ranked_jsonl, report_json, env_file


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    default_strategy = "content_based"
    ranked_jsonl, report_json, env_file = _default_paths(default_strategy)

    parser = argparse.ArgumentParser(description="将推荐 ranked 结果写入 Redis。")
    parser.add_argument(
        "--strategy",
        choices=["content_based", "two_tower"],
        default=default_strategy,
        help="写回策略类型，用于推导默认输入输出路径与默认版本号。",
    )
    parser.add_argument(
        "--ranked-jsonl",
        default=str(ranked_jsonl),
        help="ranked 输入文件路径。",
    )
    parser.add_argument(
        "--report-json",
        default=str(report_json),
        help="写回报告输出路径。",
    )
    parser.add_argument(
        "--env-file",
        default=str(env_file),
        help="环境变量文件路径（含 MySQL/Redis 连接信息）。",
    )
    parser.add_argument(
        "--key-version",
        "--version",
        dest="key_version",
        type=int,
        default=-1,
        help="Redis key 版本号，最终 key 形如 rec:user:{user_id}:v{version}。",
    )
    parser.add_argument(
        "--ttl-seconds",
        type=int,
        default=86_400,
        help="Redis 过期时间（秒）。",
    )
    parser.add_argument(
        "--max-items",
        type=int,
        default=100,
        help="每个用户写入 payload 的最大条目数。",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=500,
        help="Redis 批量写入的 pipeline 批次大小。",
    )
    parser.add_argument(
        "--strategy-override",
        default="",
        help="可选：强制覆盖 payload 中 strategy 字段。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅做映射与统计，不实际写入 Redis。",
    )
    return parser


def main() -> None:
    """执行 P5 Redis 写回。"""
    from inference.writers.redis_writeback import write_content_based_ranked_to_redis

    parser = build_argument_parser()
    args = parser.parse_args()

    default_ranked_jsonl, default_report_json, _ = _default_paths(args.strategy)

    ranked_jsonl = Path(args.ranked_jsonl)
    report_json = Path(args.report_json)
    if str(args.ranked_jsonl) == parser.get_default("ranked_jsonl"):
        ranked_jsonl = default_ranked_jsonl
    if str(args.report_json) == parser.get_default("report_json"):
        report_json = default_report_json

    key_version = args.key_version
    if key_version <= 0:
        key_version = 2 if args.strategy == "two_tower" else 1

    strategy_override = args.strategy_override.strip() or None
    if strategy_override is None and args.strategy == "two_tower":
        strategy_override = "two_tower"

    summary = write_content_based_ranked_to_redis(
        ranked_jsonl=ranked_jsonl,
        report_json=report_json,
        env_file=Path(args.env_file),
        key_version=key_version,
        ttl_seconds=args.ttl_seconds,
        max_items=args.max_items,
        batch_size=args.batch_size,
        dry_run=args.dry_run,
        strategy_override=strategy_override,
    )

    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
