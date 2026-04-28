"""结构化配置解析：将 YAML 配置文件映射为强类型 dataclass。"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class PathsConfig:
    """I/O 路径集合。"""

    user_features_csv: str
    item_features_csv: str
    train_interactions_csv: str
    test_interactions_csv: str
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

    provider: str = "oss"
    endpoint: str = "https://oss-cn-guangzhou.aliyuncs.com"
    secret_id_env: str = "OSS_ACCESS_KEY_ID"
    secret_key_env: str = "OSS_ACCESS_KEY_SECRET"


@dataclass(slots=True)
class TrainingConfig:
    """顶层配置聚合。"""

    environment: str
    seed: int
    paths: PathsConfig
    model_params: ModelParams
    train_params: TrainParams
    cloud: CloudConfig | None


def parse_config(raw: dict[str, Any]) -> TrainingConfig:
    """将原始 YAML dict 解析为 TrainingConfig。"""
    environment = str(raw.get("environment", "local")).strip().lower()
    if environment not in {"local", "cloud"}:
        raise ValueError(
            f"environment 必须为 'local' 或 'cloud'，当前值: {environment}"
        )

    seed = int(raw.get("seed", 20260428))

    # -- paths（扁平结构） --
    p = dict(raw.get("paths") or {})
    paths = PathsConfig(
        user_features_csv=str(p["user_features_csv"]),
        item_features_csv=str(p["item_features_csv"]),
        train_interactions_csv=str(p["train_interactions_csv"]),
        test_interactions_csv=str(p["test_interactions_csv"]),
        checkpoint_dir=str(p.get("checkpoint_dir", "")),
        embedding_dir=str(p.get("embedding_dir", "")),
        report_dir=str(p.get("report_dir", "")),
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

    # -- cloud（仅 cloud 环境需要） --
    cloud: CloudConfig | None = None
    if environment == "cloud":
        cc = dict(raw.get("cloud") or {})
        cloud = CloudConfig(
            provider=str(cc.get("provider", "oss")),
            endpoint=str(cc.get("endpoint", "https://oss-cn-guangzhou.aliyuncs.com")),
            secret_id_env=str(cc.get("secret_id_env", "OSS_ACCESS_KEY_ID")),
            secret_key_env=str(cc.get("secret_key_env", "OSS_ACCESS_KEY_SECRET")),
        )

    return TrainingConfig(
        environment=environment,
        seed=seed,
        paths=paths,
        model_params=model_params,
        train_params=train_params,
        cloud=cloud,
    )
