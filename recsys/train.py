"""双塔模型训练入口。

当前实现按顺序执行：
- 数据契约校验
- 样本构建
- 特征构建
- 运行上下文准备
- 模型训练与向量导出
"""

from __future__ import annotations

import argparse
import json
import time
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
            "未找到训练入口依赖。请在 recsys 目录执行："
            "uv run python train.py --config configs/two_tower/local_mvp.json"
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


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="执行 two_tower 训练全链路（数据契约、样本、特征、训练）。",
    )
    parser.add_argument(
        "--config",
        default="configs/two_tower/local_mvp.json",
        help="配置文件路径，默认 local_mvp。",
    )
    parser.add_argument(
        "--allow-external-paths",
        action="store_true",
        help="允许使用工作区外绝对路径（默认关闭以避免跨宿主机路径失效）。",
    )
    parser.add_argument(
        "--resume-run-id",
        default="",
        help="可选：指定续训的 run_id；传入后将强制启用 resume。",
    )
    return parser


def _log(message: str) -> None:
    print(f"[train] {message}", flush=True)


def run_pipeline(
    config: dict[str, Any],
    config_path: Path,
    *,
    allow_external_paths: bool,
    resume_run_id: str,
) -> dict[str, Any]:
    """执行训练流水线并返回结构化摘要。"""
    from datasets.two_tower.build_interactions import (
        build_two_tower_interactions,
    )
    from datasets.two_tower.data_contract import freeze_data_contract
    from features.two_tower.build_features import build_two_tower_features
    from training.two_tower.run_context import prepare_two_tower_run_context
    from training.two_tower.train_local_mvp import train_two_tower_local_mvp

    pipeline_cfg = dict(config.get("pipeline") or {})
    p0_cfg = dict(config.get("p0") or {})
    p1_cfg = dict(config.get("p1") or {})
    p2_cfg = dict(config.get("p2") or {})
    p3_cfg = dict(config.get("p3") or {})
    p4_cfg = dict(config.get("p4") or {})
    output_cfg = dict(config.get("output") or {})

    stages = [str(stage).lower() for stage in pipeline_cfg.get("stages") or []]
    if not stages:
        stages = ["p0", "p1", "p2", "p3", "p4"]

    input_cfg = dict(config.get("input") or {})
    input_paths = {
        "users_csv": resolve_workspace_path(
            str(input_cfg["users_csv"]),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        ),
        "songs_csv": resolve_workspace_path(
            str(input_cfg["songs_csv"]),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        ),
        "play_histories_csv": resolve_workspace_path(
            str(input_cfg["play_histories_csv"]),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        ),
        "play_counts_csv": resolve_workspace_path(
            str(input_cfg["play_counts_csv"]),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        ),
        "user_preference_csv": resolve_workspace_path(
            str(input_cfg["user_preference_csv"]),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        ),
        "song_genre_csv": resolve_workspace_path(
            str(input_cfg["song_genre_csv"]),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        ),
    }

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
    features_dir = resolve_workspace_path(
        str(output_cfg.get("features_dir") or "recsys/artifacts/two_tower/features"),
        workspace_root=WORKSPACE_ROOT,
        allow_external_paths=allow_external_paths,
    )
    reports_dir = resolve_workspace_path(
        str(output_cfg.get("reports_dir") or "recsys/artifacts/two_tower/reports"),
        workspace_root=WORKSPACE_ROOT,
        allow_external_paths=allow_external_paths,
    )

    reports_dir.mkdir(parents=True, exist_ok=True)
    datasets_dir.mkdir(parents=True, exist_ok=True)
    features_dir.mkdir(parents=True, exist_ok=True)

    train_jsonl = datasets_dir / "interactions_train.jsonl"
    valid_jsonl = datasets_dir / "interactions_valid.jsonl"
    test_jsonl = datasets_dir / "interactions_test.jsonl"

    user_features_jsonl = features_dir / "user_features.jsonl"
    item_features_jsonl = features_dir / "item_features.jsonl"
    feature_dict_json = features_dir / "feature_dictionaries.json"

    summaries: dict[str, Any] = {
        "config": {
            "config_path": str(config_path),
            "schema_version": config.get("schema_version"),
            "stages": stages,
        }
    }

    _log("开始执行训练流水线：" + ", ".join(stage.upper() for stage in stages))

    if "p0" in stages:
        stage_begin = time.perf_counter()
        _log("P0 开始：数据契约冻结与校验。")
        schema_path = resolve_workspace_path(
            str(p0_cfg.get("schema_json") or "recsys/configs/two_tower/schema_v1.json"),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        )
        schema = _load_json(schema_path)

        p0_summary = freeze_data_contract(
            input_paths=input_paths,
            required_columns=dict(schema.get("required_columns") or {}),
            field_dictionary=dict(schema.get("field_dictionary") or {}),
            id_mapping=dict(schema.get("id_mapping") or {}),
            missing_value_policy=dict(schema.get("missing_value_policy") or {}),
            split_policy={
                "train_ratio": float(p1_cfg.get("train_ratio", 0.8)),
                "valid_ratio": float(p1_cfg.get("valid_ratio", 0.1)),
                "test_ratio": float(p1_cfg.get("test_ratio", 0.1)),
            },
            negative_sampling_policy={
                "positive_target_threshold": int(
                    p1_cfg.get("positive_target_threshold", 1)
                ),
                "negative_sampling_ratio": int(
                    p1_cfg.get("negative_sampling_ratio", 2)
                ),
                "min_user_positive_events": int(
                    p1_cfg.get("min_user_positive_events", 1)
                ),
            },
            output_json=reports_dir / "p0_data_contract_report.json",
        )
        summaries["p0"] = asdict(p0_summary)
        _log(
            f"P0 完成，用时 {time.perf_counter() - stage_begin:.1f}s，"
            f"报告: {reports_dir / 'p0_data_contract_report.json'}"
        )

    if "p1" in stages:
        stage_begin = time.perf_counter()
        _log("P1 开始：构建交互样本。")
        sample_limit_value = p1_cfg.get("sample_limit", 200_000)
        sample_limit = None if sample_limit_value is None else int(sample_limit_value)

        p1_summary = build_two_tower_interactions(
            users_csv=input_paths["users_csv"],
            songs_csv=input_paths["songs_csv"],
            play_histories_csv=input_paths["play_histories_csv"],
            output_train_jsonl=train_jsonl,
            output_valid_jsonl=valid_jsonl,
            output_test_jsonl=test_jsonl,
            output_meta_json=reports_dir / "p1_interactions_report.json",
            positive_target_threshold=int(p1_cfg.get("positive_target_threshold", 1)),
            negative_sampling_ratio=int(p1_cfg.get("negative_sampling_ratio", 2)),
            train_ratio=float(p1_cfg.get("train_ratio", 0.8)),
            valid_ratio=float(p1_cfg.get("valid_ratio", 0.1)),
            test_ratio=float(p1_cfg.get("test_ratio", 0.1)),
            min_user_positive_events=int(p1_cfg.get("min_user_positive_events", 1)),
            seed=int(pipeline_cfg.get("seed", 20260410)),
            sample_limit=sample_limit,
        )
        summaries["p1"] = asdict(p1_summary)
        _log(
            f"P1 完成，用时 {time.perf_counter() - stage_begin:.1f}s，"
            f"train/valid/test={p1_summary.train_rows}/{p1_summary.valid_rows}/{p1_summary.test_rows}"
        )

    if "p2" in stages:
        stage_begin = time.perf_counter()
        _log("P2 开始：构建用户/歌曲特征。")
        p2_summary = build_two_tower_features(
            users_csv=input_paths["users_csv"],
            songs_csv=input_paths["songs_csv"],
            play_counts_csv=input_paths["play_counts_csv"],
            user_preference_csv=input_paths["user_preference_csv"],
            song_genre_csv=input_paths["song_genre_csv"],
            interactions_paths=[train_jsonl, valid_jsonl, test_jsonl],
            output_user_features_jsonl=user_features_jsonl,
            output_item_features_jsonl=item_features_jsonl,
            output_dictionary_json=feature_dict_json,
            output_report_json=reports_dir / "p2_features_report.json",
            age_bins=[int(value) for value in p2_cfg.get("age_bins") or [18, 25, 35]],
            song_length_bins=[
                int(value)
                for value in p2_cfg.get("song_length_bins")
                or [60_000, 180_000, 300_000]
            ],
        )
        summaries["p2"] = asdict(p2_summary)
        _log(
            f"P2 完成，用时 {time.perf_counter() - stage_begin:.1f}s，"
            f"user_features={user_features_jsonl.name} item_features={item_features_jsonl.name}"
        )

    p3_summary = None
    if "p3" in stages or "p4" in stages:
        training_config = dict(p4_cfg.get("training") or p3_cfg.get("training") or {})
        resume_enabled = _to_bool(training_config.get("resume", False))
        resume_run_id_text = resume_run_id.strip()
        if resume_run_id_text:
            resume_enabled = True

        stage_begin = time.perf_counter()
        _log("P3 开始：准备训练运行上下文。")
        p3_summary = prepare_two_tower_run_context(
            config=config,
            config_path=config_path,
            artifacts_root=artifacts_root,
            dataset_paths={
                "interactions_train": train_jsonl,
                "interactions_valid": valid_jsonl,
                "interactions_test": test_jsonl,
            },
            feature_paths={
                "user_features": user_features_jsonl,
                "item_features": item_features_jsonl,
                "feature_dictionaries": feature_dict_json,
            },
            context_report_json=reports_dir / "p3_run_context_report.json",
            resume=resume_enabled,
            resume_run_id=resume_run_id_text or None,
        )
        if "p3" in stages:
            summaries["p3"] = asdict(p3_summary)
        _log(
            f"P3 完成，用时 {time.perf_counter() - stage_begin:.1f}s，"
            f"run_id={p3_summary.run_id}"
        )

    if "p4" in stages:
        if p3_summary is None:
            raise RuntimeError("执行训练前必须先准备运行上下文。")

        training_config = dict(p4_cfg.get("training") or p3_cfg.get("training") or {})
        resume_run_id_text = resume_run_id.strip()
        if resume_run_id_text:
            training_config["resume"] = True

        stage_begin = time.perf_counter()
        _log("P4 开始：模型训练与向量导出。")
        p4_summary = train_two_tower_local_mvp(
            interactions_train_jsonl=train_jsonl,
            interactions_valid_jsonl=valid_jsonl,
            run_dir=Path(p3_summary.run_dir),
            report_json=reports_dir / "p4_training_report.json",
            training_config=training_config,
            seed=int(pipeline_cfg.get("seed", 20260410)),
        )
        summaries["p4"] = asdict(p4_summary)
        _log(
            f"P4 完成，用时 {time.perf_counter() - stage_begin:.1f}s，"
            f"best_epoch={p4_summary.best_epoch} best_valid_loss={p4_summary.best_valid_loss}"
        )

    _log("训练流水线执行结束。")

    return summaries


def main() -> None:
    """命令行入口。"""
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

    try:
        summary = run_pipeline(
            config=config,
            config_path=config_path,
            allow_external_paths=allow_external_paths,
            resume_run_id=str(args.resume_run_id or ""),
        )
    except KeyboardInterrupt:
        _log("检测到 Ctrl+C，训练已中断。若已启用 resume，下次可从 checkpoint 继续。")
        raise SystemExit(130)

    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
