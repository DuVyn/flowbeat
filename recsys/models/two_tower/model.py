"""P4：Two-Tower 模型定义。"""

from __future__ import annotations

import torch
from torch import nn


class _ProjectionTower(nn.Module):
    """将稀疏 ID Embedding 投影到对齐向量空间。"""

    def __init__(
        self,
        *,
        input_dim: int,
        hidden_dims: list[int],
        output_dim: int,
        dropout: float,
    ) -> None:
        super().__init__()

        dims = [input_dim, *hidden_dims]
        layers: list[nn.Module] = []

        for in_dim, out_dim in zip(dims, dims[1:]):
            layers.append(nn.Linear(in_dim, out_dim))
            layers.append(nn.ReLU())
            if dropout > 0:
                layers.append(nn.Dropout(dropout))

        last_dim = dims[-1]
        if last_dim != output_dim:
            layers.append(nn.Linear(last_dim, output_dim))

        self.network = nn.Sequential(*layers) if layers else nn.Identity()

    def forward(self, embeddings: torch.Tensor) -> torch.Tensor:
        return self.network(embeddings)


class TwoTowerModel(nn.Module):
    """双塔召回模型（用户塔 + 物品塔）。"""

    def __init__(
        self,
        *,
        num_users: int,
        num_items: int,
        embedding_dim: int,
        hidden_dims: list[int],
        dropout: float,
    ) -> None:
        super().__init__()

        if num_users <= 0:
            raise ValueError("num_users 必须 > 0")
        if num_items <= 0:
            raise ValueError("num_items 必须 > 0")
        if embedding_dim <= 0:
            raise ValueError("embedding_dim 必须 > 0")

        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.item_embedding = nn.Embedding(num_items, embedding_dim)

        self.user_tower = _ProjectionTower(
            input_dim=embedding_dim,
            hidden_dims=hidden_dims,
            output_dim=embedding_dim,
            dropout=dropout,
        )
        self.item_tower = _ProjectionTower(
            input_dim=embedding_dim,
            hidden_dims=hidden_dims,
            output_dim=embedding_dim,
            dropout=dropout,
        )

        nn.init.normal_(self.user_embedding.weight, mean=0.0, std=0.02)
        nn.init.normal_(self.item_embedding.weight, mean=0.0, std=0.02)

    def encode_user(self, user_ids: torch.Tensor) -> torch.Tensor:
        user_base = self.user_embedding(user_ids)
        return self.user_tower(user_base)

    def encode_item(self, item_ids: torch.Tensor) -> torch.Tensor:
        item_base = self.item_embedding(item_ids)
        return self.item_tower(item_base)

    def forward(self, user_ids: torch.Tensor, item_ids: torch.Tensor) -> torch.Tensor:
        user_vector = self.encode_user(user_ids)
        item_vector = self.encode_item(item_ids)
        return (user_vector * item_vector).sum(dim=1)
