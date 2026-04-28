"""数据加载引擎：从 CSV 构建 PyTorch DataLoader。"""

from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from typing import Any

import torch
from torch.utils.data import DataLoader, Dataset

from training.two_tower.config_schema import TrainParams
from training.two_tower.storage_backend import StorageBackend


@dataclass(slots=True)
class DataSummary:
    num_users: int
    num_items: int
    train_samples: int
    test_samples: int
    user_to_idx: dict[int, int]
    item_to_idx: dict[int, int]


class InteractionDataset(Dataset):
    def __init__(self, user_ids: torch.Tensor, item_ids: torch.Tensor, labels: torch.Tensor):
        self.user_ids = user_ids
        self.item_ids = item_ids
        self.labels = labels

    def __len__(self):
        return self.user_ids.shape[0]

    def __getitem__(self, idx):
        return self.user_ids[idx], self.item_ids[idx], self.labels[idx]


def _build_id_map(train_df, test_df, col):
    all_ids = sorted(set(train_df[col].unique()) | set(test_df[col].unique()))
    return {raw: i + 1 for i, raw in enumerate(all_ids)}  # 0 = UNK


def _to_tensors(df, u2i, i2i):
    u = torch.tensor(df["user_id"].map(u2i).fillna(0).astype("int64").values, dtype=torch.long)
    i = torch.tensor(df["song_id"].map(i2i).fillna(0).astype("int64").values, dtype=torch.long)
    l = torch.tensor(df["label"].astype("float32").values, dtype=torch.float32)
    return u, i, l


def _worker_init(wid, *, seed):
    torch.manual_seed(seed + wid)


def load_datasets(
    backend: StorageBackend,
    *,
    train_csv: str,
    test_csv: str,
    train_params: TrainParams,
    seed: int,
) -> tuple[DataLoader, DataLoader, DataSummary]:
    print("[DataEngine] 加载训练集...", flush=True)
    train_df = backend.read_csv(train_csv)
    print(f"[DataEngine] 训练集: {len(train_df)} 条", flush=True)

    print("[DataEngine] 加载测试集...", flush=True)
    test_df = backend.read_csv(test_csv)
    print(f"[DataEngine] 测试集: {len(test_df)} 条", flush=True)

    u2i = _build_id_map(train_df, test_df, "user_id")
    i2i = _build_id_map(train_df, test_df, "song_id")
    num_users = len(u2i) + 1
    num_items = len(i2i) + 1
    print(f"[DataEngine] num_users={num_users}, num_items={num_items}", flush=True)

    train_ds = InteractionDataset(*_to_tensors(train_df, u2i, i2i))
    test_ds = InteractionDataset(*_to_tensors(test_df, u2i, i2i))

    nw = max(0, train_params.num_workers)
    kw: dict[str, Any] = {"batch_size": train_params.batch_size, "num_workers": nw}
    if nw > 0:
        kw["pin_memory"] = train_params.pin_memory
        kw["persistent_workers"] = True
        kw["prefetch_factor"] = 2
        kw["worker_init_fn"] = partial(_worker_init, seed=seed)

    train_loader = DataLoader(train_ds, shuffle=True, **kw)
    test_loader = DataLoader(test_ds, shuffle=False, **kw)

    return train_loader, test_loader, DataSummary(
        num_users=num_users, num_items=num_items,
        train_samples=len(train_ds), test_samples=len(test_ds),
        user_to_idx=u2i, item_to_idx=i2i,
    )
