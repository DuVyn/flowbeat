"""Two-Tower P5-P7 推理入口。"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any

CURRENT_FILE = Path(__file__).resolve()
RECSYS_ROOT = CURRENT_FILE.parent
WORKSPACE_ROOT = RECSYS_ROOT.parent


def _ensure_runtime_paths() -> None:
    for path_candidate in (WORKSPACE_ROOT, RECSYS_ROOT):
        path_str = str(path_candidate)
        if path_str not in sys.path:
            sys.path.insert(0, path_str)


def _resolve_existing_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path

    name_candidates = [path.name]
    if not path.suffix:
        name_candidates.append(f"{path.name}.json")

    candidates = [
        (Path.cwd() / path).resolve(),
        (RECSYS_ROOT / path).resolve(),
        (WORKSPACE_ROOT / path).resolve(),
    ]
    for name in name_candidates:
        candidates.extend(
            [
                (RECSYS_ROOT / "configs" / "two_tower" / name).resolve(),
                (RECSYS_ROOT / "configs" / name).resolve(),
                (WORKSPACE_ROOT / "recsys" / "configs" / "two_tower" / name).resolve(),
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def _resolve_workspace_path(path_text: str) -> Path:
    path = Path(path_text)
    if path.is_absolute():
        return path
    return (WORKSPACE_ROOT / path).resolve()


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_p4_embeddings_from_report(p4_report_path: Path) -> dict[str, Path]:
    report = _load_json(p4_report_path)
    embeddings = dict(report.get("embeddings") or {})

    required = {
        "user_embeddings": "user_embeddings",
        "item_embeddings": "item_embeddings",
        "user_index": "user_index",
        "item_index": "item_index",
    }
    resolved: dict[str, Path] = {}

    for key, report_key in required.items():
        path_text = str(embeddings.get(report_key) or "").strip()
        if not path_text:
            raise RuntimeError(f"P4 报告缺少字段: embeddings.{report_key}")
        resolved[key] = _resolve_workspace_path(path_text)

    return resolved


def _resolve_p4_artifacts(
    *,
    artifacts_root: Path,
    reports_dir: Path,
    run_id: str | None,
) -> dict[str, Path]:
    if run_id:
        run_dir = artifacts_root / "runs" / run_id
        embeddings_dir = run_dir / "embeddings"
        resolved = {
            "run_dir": run_dir,
            "user_embeddings": embeddings_dir / "user_embeddings.pt",
            "item_embeddings": embeddings_dir / "item_embeddings.pt",
            "user_index": embeddings_dir / "user_index.json",
            "item_index": embeddings_dir / "item_index.json",
        }
    else:
        p4_report_path = reports_dir / "p4_training_report.json"
        if not p4_report_path.exists():
            raise RuntimeError(
                "未找到 p4_training_report.json，请先完成 P4 训练，"
                "或通过 --run-id 显式指定训练运行目录。"
            )

        embedding_paths = _read_p4_embeddings_from_report(p4_report_path)
        run_dir = embedding_paths["user_embeddings"].parent.parent
        resolved = {
            "run_dir": run_dir,
            **embedding_paths,
        }

    for key in ("user_embeddings", "item_embeddings", "user_index", "item_index"):
        path = resolved[key]
        if not path.exists():
            raise RuntimeError(f"P4 产物不存在: {path}")

    return resolved


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="执行 two_tower 的 P5-P7 流水线。",
    )
    parser.add_argument(
        "--config",
        default="configs/two_tower/local_mvp.json",
        help="配置文件路径，默认 local_mvp。",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="可选：指定 P4 训练 run_id；为空时自动读取 p4_training_report.json。",
    )
    parser.add_argument(
        "--top-k-items",
        type=int,
        default=100,
        help="P6 每用户输出推荐数量。",
    )
    parser.add_argument(
        "--score-batch-size",
        type=int,
        default=64,
        help="P6 打分批大小，显存不足时可调小。",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="推理设备：auto/cuda/cpu。",
    )
    parser.add_argument(
        "--write-redis",
        action="store_true",
        help="是否执行 P7 写回 Redis。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅用于 P7：只统计不写 Redis。",
    )
    parser.add_argument(
        "--key-version",
        type=int,
        default=2,
        help="P7 Redis key 版本号（two_tower 建议 v2）。",
    )
    parser.add_argument(
        "--ttl-seconds",
        type=int,
        default=86_400,
        help="P7 Redis 过期时间（秒）。",
    )
    parser.add_argument(
        "--redis-batch-size",
        type=int,
        default=500,
        help="P7 Redis pipeline 批量大小。",
    )
    parser.add_argument(
        "--redis-max-items",
        type=int,
        default=100,
        help="P7 payload 每用户保留条数。",
    )
    parser.add_argument(
        "--redis-report-json",
        default="",
        help="P7 写回报告路径；为空时默认输出到 two_tower/reports。",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="P7 环境变量文件路径（用于 MySQL/Redis 连接）。",
    )
    return parser


def run_pipeline(config: dict[str, Any], config_path: Path, args: argparse.Namespace):
    _ensure_runtime_paths()

    from evaluation.two_tower.offline_eval import evaluate_two_tower_ranked_results
    from inference.two_tower.rank_scoring import build_two_tower_topk_from_embeddings
    from inference.writers.redis_writeback import write_content_based_ranked_to_redis

    output_cfg = dict(config.get("output") or {})
    p3_cfg = dict(config.get("p3") or {})

    artifacts_root = _resolve_workspace_path(
        str(output_cfg.get("artifacts_root") or "recsys/artifacts/two_tower")
    )
    datasets_dir = _resolve_workspace_path(
        str(output_cfg.get("datasets_dir") or "recsys/artifacts/two_tower/datasets")
    )
    reports_dir = _resolve_workspace_path(
        str(output_cfg.get("reports_dir") or "recsys/artifacts/two_tower/reports")
    )

    interactions_train_jsonl = datasets_dir / "interactions_train.jsonl"
    interactions_test_jsonl = datasets_dir / "interactions_test.jsonl"
    if not interactions_train_jsonl.exists() or not interactions_test_jsonl.exists():
        raise RuntimeError(
            "缺少 P1 产物 interactions_train/test.jsonl，请先执行 train.py"
        )

    p4_artifacts = _resolve_p4_artifacts(
        artifacts_root=artifacts_root,
        reports_dir=reports_dir,
        run_id=args.run_id.strip() or None,
    )

    ranked_dir = artifacts_root / "ranked"
    ranked_jsonl = ranked_dir / "user_topk_scored.jsonl"
    p5_report_json = reports_dir / "p5_evaluation_report.json"

    p6_summary = build_two_tower_topk_from_embeddings(
        user_embedding_path=p4_artifacts["user_embeddings"],
        item_embedding_path=p4_artifacts["item_embeddings"],
        user_index_json=p4_artifacts["user_index"],
        item_index_json=p4_artifacts["item_index"],
        interactions_train_jsonl=interactions_train_jsonl,
        output_jsonl=ranked_jsonl,
        top_k_items=int(args.top_k_items),
        score_batch_size=int(args.score_batch_size),
        device=str(args.device),
    )

    evaluation_ks = [
        int(k) for k in (p3_cfg.get("evaluation_k") or [10, 50]) if int(k) > 0
    ]
    p5_summary = evaluate_two_tower_ranked_results(
        ranked_jsonl=ranked_jsonl,
        interactions_train_jsonl=interactions_train_jsonl,
        interactions_test_jsonl=interactions_test_jsonl,
        item_index_json=p4_artifacts["item_index"],
        report_json=p5_report_json,
        ks=evaluation_ks,
    )

    result: dict[str, Any] = {
        "config": {
            "config_path": str(config_path),
            "schema_version": config.get("schema_version"),
            "run_dir": str(p4_artifacts["run_dir"]),
        },
        "p6": asdict(p6_summary),
        "p5": asdict(p5_summary),
    }

    if args.write_redis:
        redis_report_json = (
            _resolve_workspace_path(str(args.redis_report_json))
            if str(args.redis_report_json).strip()
            else reports_dir / "two_tower_redis_report.json"
        )

        p7_summary = write_content_based_ranked_to_redis(
            ranked_jsonl=ranked_jsonl,
            report_json=redis_report_json,
            env_file=_resolve_workspace_path(str(args.env_file)),
            key_version=int(args.key_version),
            ttl_seconds=int(args.ttl_seconds),
            max_items=int(args.redis_max_items),
            batch_size=int(args.redis_batch_size),
            dry_run=bool(args.dry_run),
            strategy_override="two_tower",
        )
        result["p7"] = asdict(p7_summary)

    return result


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    config_path = _resolve_existing_path(str(args.config))
    config = _load_json(config_path)

    summary = run_pipeline(config=config, config_path=config_path, args=args)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
