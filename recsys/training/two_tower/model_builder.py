"""模型构建器：根据配置参数实例化双塔模型。"""

from __future__ import annotations

import warnings

import torch
from torch import nn

from models.two_tower.model import TwoTowerModel
from training.two_tower.config_schema import ModelParams


def build_model(
    model_params: ModelParams,
    *,
    num_users: int,
    num_items: int,
) -> TwoTowerModel:
    """根据配置构建 TwoTowerModel 实例。"""
    return TwoTowerModel(
        num_users=num_users,
        num_items=num_items,
        embedding_dim=model_params.embedding_dim,
        hidden_dims=model_params.hidden_units,
        dropout=model_params.dropout,
    )


def resolve_device(requested: str) -> torch.device:
    """解析设备字符串，自动检测可用硬件。"""
    name = requested.strip().lower()
    has_mps = (
        getattr(torch.backends, "mps", None)
        and torch.backends.mps.is_available()
        and torch.backends.mps.is_built()
    )

    if name == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if has_mps:
            return torch.device("mps")
        return torch.device("cpu")

    if name == "cuda" and not torch.cuda.is_available():
        warnings.warn("CUDA 不可用，回退到 CPU。", stacklevel=2)
        return torch.device("cpu")

    if name == "mps" and not has_mps:
        warnings.warn("MPS 不可用，回退到 CPU。", stacklevel=2)
        return torch.device("cpu")

    return torch.device(name)
