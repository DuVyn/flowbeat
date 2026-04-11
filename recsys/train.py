"""Two-Tower P0-P4 训练入口。

当前实现覆盖：
- P0 数据口径冻结
- P1 样本构建
- P2 特征工程
- P3 训练配置与运行上下文准备
- P4 本地最小可行训练
"""

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
    """补齐运行时导入路径，兼容从不同目录触发脚本。"""
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


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="执行 two_tower 的 P0-P4 流水线。",
    )
    parser.add_argument(
        "--config",
        default="configs/two_tower/local_mvp.json",
        help="配置文件路径，默认 local_mvp。",
    )
    return parser


def run_pipeline(config: dict[str, Any], config_path: Path) -> dict[str, Any]:
    """执行 P0-P4 阶段并返回结构化摘要。"""
    _ensure_runtime_paths()

    from datasets.two_tower.build_interactions import build_two_tower_interactions
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
        "users_csv": _resolve_workspace_path(str(input_cfg["users_csv"])),
        "songs_csv": _resolve_workspace_path(str(input_cfg["songs_csv"])),
        "play_histories_csv": _resolve_workspace_path(
            str(input_cfg["play_histories_csv"])
        ),
        "play_counts_csv": _resolve_workspace_path(str(input_cfg["play_counts_csv"])),
        "user_preference_csv": _resolve_workspace_path(
            str(input_cfg["user_preference_csv"])
        ),
        "song_genre_csv": _resolve_workspace_path(str(input_cfg["song_genre_csv"])),
    }

    artifacts_root = _resolve_workspace_path(
        str(output_cfg.get("artifacts_root") or "recsys/artifacts/two_tower")
    )
    datasets_dir = _resolve_workspace_path(
        str(output_cfg.get("datasets_dir") or "recsys/artifacts/two_tower/datasets")
    )
    features_dir = _resolve_workspace_path(
        str(output_cfg.get("features_dir") or "recsys/artifacts/two_tower/features")
    )
    reports_dir = _resolve_workspace_path(
        str(output_cfg.get("reports_dir") or "recsys/artifacts/two_tower/reports")
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

    if "p0" in stages:
        schema_path = _resolve_workspace_path(
            str(p0_cfg.get("schema_json") or "recsys/configs/two_tower/schema_v1.json")
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

    if "p1" in stages:
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

    if "p2" in stages:
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

    p3_summary = None
    if "p3" in stages or "p4" in stages:
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
        )
        if "p3" in stages:
            summaries["p3"] = asdict(p3_summary)

    if "p4" in stages:
        if p3_summary is None:
            raise RuntimeError("执行 P4 前必须先准备 P3 运行上下文。")

        training_config = dict(p4_cfg.get("training") or p3_cfg.get("training") or {})
        p4_summary = train_two_tower_local_mvp(
            interactions_train_jsonl=train_jsonl,
            interactions_valid_jsonl=valid_jsonl,
            run_dir=Path(p3_summary.run_dir),
            report_json=reports_dir / "p4_training_report.json",
            training_config=training_config,
            seed=int(pipeline_cfg.get("seed", 20260410)),
        )
        summaries["p4"] = asdict(p4_summary)

    return summaries


def main() -> None:
    """命令行入口。"""
    parser = build_argument_parser()
    args = parser.parse_args()

    config_path = _resolve_existing_path(str(args.config))
    config = _load_json(config_path)

    summary = run_pipeline(config=config, config_path=config_path)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
