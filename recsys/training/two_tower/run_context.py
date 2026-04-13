"""Two-Tower 训练配置与运行上下文准备。"""

from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch


@dataclass(slots=True)
class TwoTowerRunContextSummary:
    """训练运行上下文摘要。"""

    run_id: str
    experiment_name: str
    seed: int
    config_hash: str
    run_dir: str
    context_report_path: str


def _json_hash(payload: dict[str, Any]) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _prepare_seed(seed: int) -> None:
    """统一设置随机种子，保证同配置下可复现。"""
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def prepare_two_tower_run_context(
    *,
    config: dict[str, Any],
    config_path: Path,
    artifacts_root: Path,
    dataset_paths: dict[str, Path],
    feature_paths: dict[str, Path],
    context_report_json: Path,
) -> TwoTowerRunContextSummary:
    """根据训练配置生成 run_id、配置快照与日志模板。"""
    pipeline_config = dict(config.get("pipeline") or {})
    p3_config = dict(config.get("p3") or {})

    seed = int(pipeline_config.get("seed", 20260410))
    experiment_name = str(p3_config.get("experiment_name") or "two_tower")

    _prepare_seed(seed)

    config_hash = _json_hash(config)
    utc_now = datetime.now(timezone.utc)
    run_id = f"{experiment_name}_{utc_now.strftime('%Y%m%d_%H%M%S')}"

    run_dir = artifacts_root / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    snapshot = {
        "generated_at": utc_now.isoformat(),
        "run_id": run_id,
        "config_path": str(config_path),
        "config_hash": config_hash,
        "seed": seed,
        "pipeline_stages": list(pipeline_config.get("stages") or []),
        "p3": p3_config,
        "dataset_paths": {key: str(value) for key, value in dataset_paths.items()},
        "feature_paths": {key: str(value) for key, value in feature_paths.items()},
    }

    snapshot_path = run_dir / "config_snapshot.json"
    snapshot_path.write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 训练日志模板用于后续训练过程直接填充，不再临时定义字段。
    log_template = {
        "run_id": run_id,
        "log_schema_version": "two_tower_train_log_v1",
        "fields": [
            "timestamp",
            "epoch",
            "step",
            "split",
            "loss",
            "auc",
            "recall_at_k",
            "ndcg_at_k",
            "learning_rate",
        ],
        "notes": "训练阶段按该字段结构持续追加日志。",
    }
    log_template_path = run_dir / "training_log_template.json"
    log_template_path.write_text(
        json.dumps(log_template, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    context_report = {
        "generated_at": utc_now.isoformat(),
        "summary": {
            "run_id": run_id,
            "experiment_name": experiment_name,
            "seed": seed,
            "config_hash": config_hash,
            "run_dir": str(run_dir),
        },
        "artifacts": {
            "config_snapshot": str(snapshot_path),
            "training_log_template": str(log_template_path),
        },
    }

    context_report_json.parent.mkdir(parents=True, exist_ok=True)
    context_report_json.write_text(
        json.dumps(context_report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return TwoTowerRunContextSummary(
        run_id=run_id,
        experiment_name=experiment_name,
        seed=seed,
        config_hash=config_hash,
        run_dir=str(run_dir),
        context_report_path=str(context_report_json),
    )
