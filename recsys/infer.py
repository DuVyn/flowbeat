"""双塔模型推理入口。"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

try:
    from runtime_paths import (
        detect_workspace_root,
        resolve_existing_config_path,
        resolve_workspace_path,
    )
except ModuleNotFoundError as exc:
    if __name__ == "__main__":
        raise RuntimeError(
            "未找到推理入口依赖。请在 recsys 目录执行："
            "uv run python infer.py --config configs/two_tower/local_mvp.json"
        ) from exc
    raise


CURRENT_FILE = Path(__file__).resolve()
RECSYS_ROOT = CURRENT_FILE.parent
WORKSPACE_ROOT = detect_workspace_root(anchor_file=CURRENT_FILE)


def _to_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    return text in {"1", "true", "yes", "on"}


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_reported_path(
    path_text: str,
    *,
    run_dir: Path,
    allow_external_paths: bool,
) -> Path:
    path = Path(path_text).expanduser()
    if path.is_absolute():
        return resolve_workspace_path(
            str(path),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        )
    return (run_dir / path).resolve()


def _read_training_artifacts_from_report(
    p4_report_path: Path,
    *,
    allow_external_paths: bool,
) -> dict[str, Path]:
    report = _load_json(p4_report_path)
    embeddings = dict(report.get("embeddings") or {})

    run_dir_text = str(
        report.get("run_dir")
        or (dict(report.get("artifacts") or {}).get("run_dir"))
        or ""
    ).strip()
    run_dir: Path | None = None
    if run_dir_text:
        run_dir = resolve_workspace_path(
            run_dir_text,
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        )

    required = {
        "user_embeddings": "user_embeddings",
        "item_embeddings": "item_embeddings",
        "user_index": "user_index",
        "item_index": "item_index",
    }
    resolved: dict[str, Path] = {"run_dir": run_dir} if run_dir else {}

    for key, report_key in required.items():
        path_text = str(embeddings.get(report_key) or "").strip()
        if not path_text:
            raise RuntimeError(f"训练报告缺少字段: embeddings.{report_key}")

        if run_dir is None and not Path(path_text).is_absolute():
            raise RuntimeError(
                "训练报告使用了相对路径，但缺少 run_dir，无法恢复产物绝对路径。"
            )

        if run_dir is not None:
            resolved[key] = _resolve_reported_path(
                path_text,
                run_dir=run_dir,
                allow_external_paths=allow_external_paths,
            )
            continue

        resolved[key] = resolve_workspace_path(
            path_text,
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        )

    if "run_dir" not in resolved:
        resolved["run_dir"] = resolved["user_embeddings"].parent.parent

    return resolved


def _resolve_p4_artifacts(
    *,
    artifacts_root: Path,
    reports_dir: Path,
    run_id: str | None,
    allow_external_paths: bool,
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
                "未找到 p4_training_report.json，请先完成训练，"
                "或通过 --run-id 显式指定训练运行目录。"
            )

        resolved = _read_training_artifacts_from_report(
            p4_report_path,
            allow_external_paths=allow_external_paths,
        )

    for key in ("user_embeddings", "item_embeddings", "user_index", "item_index"):
        path = resolved[key]
        if not path.exists():
            raise RuntimeError(f"训练产物不存在: {path}")

    return resolved


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="执行 two_tower 推理与可选写回流程。",
    )
    parser.add_argument(
        "--config",
        default="configs/two_tower/local_mvp.json",
        help="配置文件路径，默认 local_mvp。",
    )
    parser.add_argument(
        "--run-id",
        default="",
        help="可选：指定训练 run_id；为空时自动读取 p4_training_report.json。",
    )
    parser.add_argument(
        "--top-k-items",
        type=int,
        default=100,
        help="每用户输出推荐数量。",
    )
    parser.add_argument(
        "--score-batch-size",
        type=int,
        default=64,
        help="用户批次大小，显存不足时可调小。",
    )
    parser.add_argument(
        "--item-block-size",
        type=int,
        default=20_000,
        help="物品向量分块大小，避免一次性将全量 item 向量搬到显存。",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="推理设备：auto/cuda/mps/cpu。",
    )
    parser.add_argument(
        "--write-redis",
        action="store_true",
        help="是否将结果写回 Redis。",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="仅统计不写 Redis。",
    )
    parser.add_argument(
        "--key-version",
        type=int,
        default=2,
        help="Redis key 版本号（two_tower 建议 v2）。",
    )
    parser.add_argument(
        "--ttl-seconds",
        type=int,
        default=0,
        help="兼容保留参数，当前固定永不过期（该参数不生效）。",
    )
    parser.add_argument(
        "--redis-batch-size",
        type=int,
        default=500,
        help="Redis pipeline 批量大小。",
    )
    parser.add_argument(
        "--redis-max-items",
        type=int,
        default=100,
        help="写回 payload 每用户保留条数。",
    )
    parser.add_argument(
        "--redis-report-json",
        default="",
        help="写回报告路径；为空时默认输出到 two_tower/reports。",
    )
    parser.add_argument(
        "--env-file",
        default=".env",
        help="环境变量文件路径（用于 MySQL/Redis 连接）。",
    )
    parser.add_argument(
        "--allow-external-paths",
        action="store_true",
        help="允许使用工作区外绝对路径（默认关闭以避免跨宿主机路径失效）。",
    )
    return parser


def run_pipeline(
    config: dict[str, Any],
    config_path: Path,
    args: argparse.Namespace,
    *,
    allow_external_paths: bool,
):
    from evaluation.two_tower.offline_eval import (
        evaluate_two_tower_ranked_results,
    )
    from inference.two_tower.rank_scoring import (
        build_two_tower_topk_from_embeddings,
    )

    output_cfg = dict(config.get("output") or {})
    p3_cfg = dict(config.get("p3") or {})

    artifacts_root = resolve_workspace_path(
        str(output_cfg.get("artifacts_root") or "recsys/artifacts/two_tower"),
        workspace_root=WORKSPACE_ROOT,
        allow_external_paths=allow_external_paths,
    )
    datasets_dir = resolve_workspace_path(
        str(output_cfg.get("datasets_dir") or "recsys/artifacts/two_tower/datasets"),
        workspace_root=WORKSPACE_ROOT,
        allow_external_paths=allow_external_paths,
    )
    reports_dir = resolve_workspace_path(
        str(output_cfg.get("reports_dir") or "recsys/artifacts/two_tower/reports"),
        workspace_root=WORKSPACE_ROOT,
        allow_external_paths=allow_external_paths,
    )

    interactions_train_jsonl = datasets_dir / "interactions_train.jsonl"
    interactions_test_jsonl = datasets_dir / "interactions_test.jsonl"
    if not interactions_train_jsonl.exists() or not interactions_test_jsonl.exists():
        raise RuntimeError(
            "缺少 interactions_train/test.jsonl，请先执行训练入口生成样本。"
        )

    p4_artifacts = _resolve_p4_artifacts(
        artifacts_root=artifacts_root,
        reports_dir=reports_dir,
        run_id=args.run_id.strip() or None,
        allow_external_paths=allow_external_paths,
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
        item_block_size=int(args.item_block_size),
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
        from inference.writers.redis_writeback import (
            write_content_based_ranked_to_redis,
        )

        redis_report_json = (
            resolve_workspace_path(
                str(args.redis_report_json),
                workspace_root=WORKSPACE_ROOT,
                allow_external_paths=allow_external_paths,
            )
            if str(args.redis_report_json).strip()
            else reports_dir / "two_tower_redis_report.json"
        )

        p7_summary = write_content_based_ranked_to_redis(
            ranked_jsonl=ranked_jsonl,
            report_json=redis_report_json,
            env_file=resolve_workspace_path(
                str(args.env_file),
                workspace_root=WORKSPACE_ROOT,
                allow_external_paths=allow_external_paths,
            ),
            key_version=int(args.key_version),
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

    config_path = resolve_existing_config_path(
        str(args.config),
        workspace_root=WORKSPACE_ROOT,
        recsys_root=RECSYS_ROOT,
        allow_external_paths=True,
    )
    config = _load_json(config_path)

    pipeline_cfg = dict(config.get("pipeline") or {})
    allow_external_paths = bool(args.allow_external_paths) or _to_bool(
        pipeline_cfg.get("allow_external_paths", False)
    )

    summary = run_pipeline(
        config=config,
        config_path=config_path,
        args=args,
        allow_external_paths=allow_external_paths,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
