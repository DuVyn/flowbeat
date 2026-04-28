"""结构化配置解析：将 YAML 配置文件映射为强类型 dataclass。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# Dataclass 定义
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class PathsConfig:
    """根据环境决定的 I/O 路径集合。"""
    user_features_csv: str
    item_features_csv: str
    train_interactions_csv: str
    test_interactions_csv: str
    artifacts_dir: str
    checkpoint_dir: str
    embedding_dir: str
    report_dir: str


@dataclass(slots=True)
class ModelParams:
    """双塔网络超参数。"""
    embedding_dim: int = 64
    hidden_units: list[int] = field(default_factory=lambda: [128, 64])
    dropout: float = 0.1


@dataclass(slots=True)
class TrainParams:
    """训练相关超参数。"""
    batch_size: int = 512
    learning_rate: float = 1e-3
    weight_decay: float = 1e-5
    epochs: int = 10
    device: str = "auto"
    num_workers: int = 2
    pin_memory: bool = True
    log_every_steps: int = 200
    early_stopping_patience: int = 3
    resume: bool = False
    resume_from: str = "last"


@dataclass(slots=True)
class CloudConfig:
    """云端 SDK 相关配置。"""
    provider: str = "cos"
    region: str = "ap-guangzhou"
    secret_id_env: str = "COS_SECRET_ID"
    secret_key_env: str = "COS_SECRET_KEY"


@dataclass(slots=True)
class TrainingConfig:
    """顶层配置聚合。"""
    environment: str  # "local" | "cloud"
    seed: int
    paths: PathsConfig
    model_params: ModelParams
    train_params: TrainParams
    cloud: CloudConfig


# ---------------------------------------------------------------------------
# 解析工具
# ---------------------------------------------------------------------------

def _pick_paths(raw: dict[str, Any], environment: str) -> dict[str, Any]:
    """从 paths.<environment> 分支提取路径映射。"""
    paths_block = raw.get("paths") or {}
    env_paths = paths_block.get(environment)
    if not env_paths or not isinstance(env_paths, dict):
        raise ValueError(
            f"配置文件中缺少 paths.{environment} 分支，"
            f"可用分支: {list(paths_block.keys())}"
        )
    return dict(env_paths)


def parse_config(
    raw: dict[str, Any],
    *,
    env_override: str | None = None,
) -> TrainingConfig:
    """将原始 YAML dict 解析为 TrainingConfig。

    Parameters
    ----------
    raw : dict
        由 ``yaml.safe_load()`` 读取的字典。
    env_override : str | None
        命令行 ``--env`` 参数，若提供则覆盖配置文件中的 ``environment``。

    Returns
    -------
    TrainingConfig
        解析并校验后的结构化配置。
    """
    environment = (env_override or raw.get("environment", "local")).strip().lower()
    if environment not in {"local", "cloud"}:
        raise ValueError(f"environment 必须为 'local' 或 'cloud'，当前值: {environment}")

    seed = int(raw.get("seed", 20260428))

    # -- paths --
    env_paths = _pick_paths(raw, environment)
    paths = PathsConfig(
        user_features_csv=str(env_paths["user_features_csv"]),
        item_features_csv=str(env_paths["item_features_csv"]),
        train_interactions_csv=str(env_paths["train_interactions_csv"]),
        test_interactions_csv=str(env_paths["test_interactions_csv"]),
        artifacts_dir=str(env_paths.get("artifacts_dir", "")),
        checkpoint_dir=str(env_paths.get("checkpoint_dir", "")),
        embedding_dir=str(env_paths.get("embedding_dir", "")),
        report_dir=str(env_paths.get("report_dir", "")),
    )

    # -- model_params --
    mp = dict(raw.get("model_params") or {})
    model_params = ModelParams(
        embedding_dim=int(mp.get("embedding_dim", 64)),
        hidden_units=[int(x) for x in (mp.get("hidden_units") or [128, 64])],
        dropout=float(mp.get("dropout", 0.1)),
    )

    # -- train_params --
    tp = dict(raw.get("train_params") or {})
    train_params = TrainParams(
        batch_size=int(tp.get("batch_size", 512)),
        learning_rate=float(tp.get("learning_rate", 1e-3)),
        weight_decay=float(tp.get("weight_decay", 1e-5)),
        epochs=int(tp.get("epochs", 10)),
        device=str(tp.get("device", "auto")),
        num_workers=int(tp.get("num_workers", 2)),
        pin_memory=bool(tp.get("pin_memory", True)),
        log_every_steps=max(1, int(tp.get("log_every_steps", 200))),
        early_stopping_patience=int(tp.get("early_stopping_patience", 3)),
        resume=bool(tp.get("resume", False)),
        resume_from=str(tp.get("resume_from", "last")),
    )

    # -- cloud --
    cc = dict(raw.get("cloud") or {})
    cloud = CloudConfig(
        provider=str(cc.get("provider", "cos")),
        region=str(cc.get("region", "ap-guangzhou")),
        secret_id_env=str(cc.get("secret_id_env", "COS_SECRET_ID")),
        secret_key_env=str(cc.get("secret_key_env", "COS_SECRET_KEY")),
    )

    return TrainingConfig(
        environment=environment,
        seed=seed,
        paths=paths,
        model_params=model_params,
        train_params=train_params,
        cloud=cloud,
    )
