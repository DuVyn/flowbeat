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


def _resolve_resume_run_dir(
    *,
    artifacts_root: Path,
    context_report_json: Path,
    experiment_name: str,
    resume: bool,
    resume_run_id: str | None,
) -> Path | None:
    """解析断点续训目标 run 目录。"""
    runs_root = artifacts_root / "runs"

    if resume_run_id:
        run_dir = (runs_root / resume_run_id.strip()).resolve()
        if not run_dir.exists():
            raise FileNotFoundError(f"指定的 resume_run_id 不存在: {run_dir}")
        return run_dir

    if not resume:
        return None

    # 优先复用最近一次上下文报告中的 run_dir。
    if context_report_json.exists():
        try:
            report = json.loads(context_report_json.read_text(encoding="utf-8"))
            summary = dict(report.get("summary") or {})
            report_experiment = str(summary.get("experiment_name") or "").strip()
            run_dir_text = str(summary.get("run_dir") or "").strip()
            if report_experiment == experiment_name and run_dir_text:
                run_dir = Path(run_dir_text).expanduser()
                if not run_dir.is_absolute():
                    run_dir = (runs_root / run_dir).resolve()
                else:
                    run_dir = run_dir.resolve()
                if run_dir.exists():
                    return run_dir
        except Exception:
            # 上下文报告损坏时继续回退到目录扫描策略。
            pass

    # 回退：按实验名前缀选择最新且存在 checkpoint 的目录。
    if not runs_root.exists():
        return None

    prefix = f"{experiment_name}_"
    candidates = [
        path
        for path in runs_root.iterdir()
        if path.is_dir() and path.name.startswith(prefix)
    ]
    candidates.sort(key=lambda path: path.stat().st_mtime, reverse=True)
    for candidate in candidates:
        if (candidate / "checkpoints" / "last_model.pt").exists():
            return candidate.resolve()

    return None


def prepare_two_tower_run_context(
    *,
    config: dict[str, Any],
    config_path: Path,
    artifacts_root: Path,
    dataset_paths: dict[str, Path],
    feature_paths: dict[str, Path],
    context_report_json: Path,
    resume: bool = False,
    resume_run_id: str | None = None,
) -> TwoTowerRunContextSummary:
    """根据训练配置生成 run_id、配置快照与日志模板。"""
    pipeline_config = dict(config.get("pipeline") or {})
    p3_config = dict(config.get("p3") or {})

    seed = int(pipeline_config.get("seed", 20260410))
    experiment_name = str(p3_config.get("experiment_name") or "two_tower")

    _prepare_seed(seed)

    config_hash = _json_hash(config)
    utc_now = datetime.now(timezone.utc)
    resume_dir = _resolve_resume_run_dir(
        artifacts_root=artifacts_root,
        context_report_json=context_report_json,
        experiment_name=experiment_name,
        resume=resume,
        resume_run_id=resume_run_id,
    )
    if resume_dir is None:
        run_id = f"{experiment_name}_{utc_now.strftime('%Y%m%d_%H%M%S')}"
        run_dir = artifacts_root / "runs" / run_id
        resumed_from = None
    else:
        run_dir = resume_dir
        run_id = run_dir.name
        resumed_from = run_id

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
            "resume": bool(resume),
            "resumed_from": resumed_from,
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
