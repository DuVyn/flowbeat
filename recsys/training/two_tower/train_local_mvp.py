"""P4：Two-Tower 本地最小可行训练流程。"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset

from models.two_tower.model import TwoTowerModel


@dataclass(slots=True)
class TwoTowerTrainingSummary:
    """P4 训练摘要。"""

    run_dir: str
    device: str
    num_users: int
    num_items: int
    train_samples: int
    valid_samples: int
    epochs: int
    best_epoch: int
    best_valid_loss: float
    best_valid_auc: float
    final_train_loss: float
    final_valid_loss: float
    best_checkpoint_path: str
    last_checkpoint_path: str
    user_embedding_path: str
    item_embedding_path: str
    report_path: str


def _set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _resolve_device(device: str | None) -> torch.device:
    if device is None or device == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device == "cuda" and not torch.cuda.is_available():
        return torch.device("cpu")
    return torch.device(device)


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            yield json.loads(text)


def _to_int(value: Any, default: int = 0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _load_interactions(
    *,
    path: Path,
    user_to_idx: dict[str, int],
    item_to_idx: dict[str, int],
    allow_extend_index: bool,
) -> tuple[list[tuple[int, int, float]], int]:
    """读取交互样本并映射为索引样本。"""
    samples: list[tuple[int, int, float]] = []
    invalid_rows = 0

    for row in _iter_jsonl(path):
        user_key = str(row.get("user_key") or "").strip()
        song_id = str(row.get("song_id") or "").strip()
        if not user_key or not song_id:
            invalid_rows += 1
            continue

        label_raw = _to_int(row.get("label"), default=0)
        label = 1.0 if label_raw > 0 else 0.0

        if allow_extend_index:
            user_idx = user_to_idx.setdefault(user_key, len(user_to_idx))
            item_idx = item_to_idx.setdefault(song_id, len(item_to_idx))
        else:
            user_idx = user_to_idx.get(user_key, 0)
            item_idx = item_to_idx.get(song_id, 0)

        samples.append((user_idx, item_idx, label))

    return samples, invalid_rows


def _build_tensor_dataset(samples: list[tuple[int, int, float]]) -> TensorDataset:
    user_ids = torch.tensor([sample[0] for sample in samples], dtype=torch.long)
    item_ids = torch.tensor([sample[1] for sample in samples], dtype=torch.long)
    labels = torch.tensor([sample[2] for sample in samples], dtype=torch.float32)
    return TensorDataset(user_ids, item_ids, labels)


def _binary_auc(labels: torch.Tensor, scores: torch.Tensor) -> float:
    """基于秩统计计算 AUC。"""
    if labels.numel() == 0:
        return 0.5

    label_mask = labels > 0.5
    pos_count = int(label_mask.sum().item())
    neg_count = int((~label_mask).sum().item())

    if pos_count == 0 or neg_count == 0:
        return 0.5

    sorted_indices = torch.argsort(scores, dim=0)
    ranks = torch.empty_like(sorted_indices, dtype=torch.float32)
    ranks[sorted_indices] = torch.arange(
        1,
        sorted_indices.numel() + 1,
        dtype=torch.float32,
        device=scores.device,
    )

    rank_sum_pos = ranks[label_mask].sum().item()
    auc = (rank_sum_pos - pos_count * (pos_count + 1) / 2) / (pos_count * neg_count)
    return float(auc)


def _unpack_three_tensors(
    batch: tuple[torch.Tensor, ...],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """将 DataLoader 返回的可变元组批次收窄为三元组。"""
    if len(batch) != 3:
        raise ValueError(f"期望 batch 为 3 个张量，实际为 {len(batch)} 个。")
    return batch[0], batch[1], batch[2]


def _evaluate_epoch(
    *,
    model: TwoTowerModel,
    dataloader: DataLoader[tuple[torch.Tensor, ...]],
    criterion: nn.Module,
    device: torch.device,
) -> tuple[float, float]:
    model.eval()
    total_loss = 0.0
    total_samples = 0

    all_scores: list[torch.Tensor] = []
    all_labels: list[torch.Tensor] = []

    with torch.no_grad():
        for batch in dataloader:
            user_ids, item_ids, labels = _unpack_three_tensors(batch)
            user_ids = user_ids.to(device)
            item_ids = item_ids.to(device)
            labels = labels.to(device)

            logits = model(user_ids, item_ids)
            loss = criterion(logits, labels)

            batch_size = labels.shape[0]
            total_samples += batch_size
            total_loss += float(loss.item()) * batch_size

            all_scores.append(logits.detach())
            all_labels.append(labels.detach())

    avg_loss = total_loss / total_samples if total_samples > 0 else 0.0

    if all_scores:
        scores = torch.cat(all_scores, dim=0)
        labels = torch.cat(all_labels, dim=0)
        auc = _binary_auc(labels=labels, scores=scores)
    else:
        auc = 0.5

    return avg_loss, auc


def train_two_tower_local_mvp(
    *,
    interactions_train_jsonl: Path,
    interactions_valid_jsonl: Path,
    run_dir: Path,
    report_json: Path,
    training_config: dict[str, Any],
    seed: int,
) -> TwoTowerTrainingSummary:
    """执行 P4 本地最小训练并导出 checkpoint 与 embedding。"""
    _set_seed(seed)

    embedding_dim = int(training_config.get("embedding_dim", 64))
    hidden_dims = [int(dim) for dim in training_config.get("hidden_dims") or [128, 64]]
    dropout = float(training_config.get("dropout", 0.1))
    batch_size = int(training_config.get("batch_size", 256))
    epochs = int(training_config.get("epochs", 3))
    learning_rate = float(training_config.get("learning_rate", 1e-3))
    weight_decay = float(training_config.get("weight_decay", 1e-5))
    requested_device = str(training_config.get("device", "auto"))

    if batch_size <= 0:
        raise ValueError("batch_size 必须 > 0")
    if epochs <= 0:
        raise ValueError("epochs 必须 > 0")

    device = _resolve_device(requested_device)

    user_to_idx: dict[str, int] = {"__UNK__": 0}
    item_to_idx: dict[str, int] = {"__UNK__": 0}

    train_samples, train_invalid_rows = _load_interactions(
        path=interactions_train_jsonl,
        user_to_idx=user_to_idx,
        item_to_idx=item_to_idx,
        allow_extend_index=True,
    )
    valid_samples, valid_invalid_rows = _load_interactions(
        path=interactions_valid_jsonl,
        user_to_idx=user_to_idx,
        item_to_idx=item_to_idx,
        allow_extend_index=False,
    )

    if not train_samples:
        raise ValueError("训练集为空，无法执行 P4。")
    if not valid_samples:
        raise ValueError("验证集为空，无法执行 P4。")

    train_dataset = _build_tensor_dataset(train_samples)
    valid_dataset = _build_tensor_dataset(valid_samples)

    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    valid_loader = DataLoader(valid_dataset, batch_size=batch_size, shuffle=False)

    model = TwoTowerModel(
        num_users=len(user_to_idx),
        num_items=len(item_to_idx),
        embedding_dim=embedding_dim,
        hidden_dims=hidden_dims,
        dropout=dropout,
    ).to(device)

    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=learning_rate,
        weight_decay=weight_decay,
    )

    run_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir = run_dir / "checkpoints"
    embeddings_dir = run_dir / "embeddings"
    checkpoints_dir.mkdir(parents=True, exist_ok=True)
    embeddings_dir.mkdir(parents=True, exist_ok=True)

    best_checkpoint_path = checkpoints_dir / "best_model.pt"
    last_checkpoint_path = checkpoints_dir / "last_model.pt"

    best_epoch = 0
    best_valid_loss = float("inf")
    best_valid_auc = 0.0
    final_train_loss = 0.0
    final_valid_loss = 0.0

    history: list[dict[str, Any]] = []

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss_sum = 0.0
        train_sample_count = 0

        for batch in train_loader:
            user_ids, item_ids, labels = _unpack_three_tensors(batch)
            user_ids = user_ids.to(device)
            item_ids = item_ids.to(device)
            labels = labels.to(device)

            optimizer.zero_grad(set_to_none=True)
            logits = model(user_ids, item_ids)
            loss = criterion(logits, labels)
            loss.backward()
            optimizer.step()

            batch_size_real = labels.shape[0]
            train_loss_sum += float(loss.item()) * batch_size_real
            train_sample_count += batch_size_real

        final_train_loss = (
            train_loss_sum / train_sample_count if train_sample_count > 0 else 0.0
        )

        valid_loss, valid_auc = _evaluate_epoch(
            model=model,
            dataloader=valid_loader,
            criterion=criterion,
            device=device,
        )
        final_valid_loss = valid_loss

        history.append(
            {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "epoch": epoch,
                "train_loss": round(final_train_loss, 8),
                "valid_loss": round(valid_loss, 8),
                "valid_auc": round(valid_auc, 8),
                "learning_rate": learning_rate,
            }
        )

        if valid_loss < best_valid_loss:
            best_valid_loss = valid_loss
            best_valid_auc = valid_auc
            best_epoch = epoch
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "valid_loss": valid_loss,
                    "valid_auc": valid_auc,
                    "user_to_idx": user_to_idx,
                    "item_to_idx": item_to_idx,
                },
                best_checkpoint_path,
            )

    torch.save(
        {
            "epoch": epochs,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "user_to_idx": user_to_idx,
            "item_to_idx": item_to_idx,
        },
        last_checkpoint_path,
    )

    model.eval()
    with torch.no_grad():
        user_ids = torch.arange(len(user_to_idx), device=device, dtype=torch.long)
        item_ids = torch.arange(len(item_to_idx), device=device, dtype=torch.long)
        user_embeddings = model.encode_user(user_ids).cpu()
        item_embeddings = model.encode_item(item_ids).cpu()

    user_embedding_path = embeddings_dir / "user_embeddings.pt"
    item_embedding_path = embeddings_dir / "item_embeddings.pt"
    user_index_path = embeddings_dir / "user_index.json"
    item_index_path = embeddings_dir / "item_index.json"

    torch.save(user_embeddings, user_embedding_path)
    torch.save(item_embeddings, item_embedding_path)
    user_index_path.write_text(
        json.dumps(user_to_idx, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    item_index_path.write_text(
        json.dumps(item_to_idx, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    report_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "settings": {
            "seed": seed,
            "embedding_dim": embedding_dim,
            "hidden_dims": hidden_dims,
            "dropout": dropout,
            "batch_size": batch_size,
            "epochs": epochs,
            "learning_rate": learning_rate,
            "weight_decay": weight_decay,
            "device": str(device),
        },
        "inputs": {
            "interactions_train_jsonl": str(interactions_train_jsonl),
            "interactions_valid_jsonl": str(interactions_valid_jsonl),
        },
        "data_summary": {
            "num_users": len(user_to_idx),
            "num_items": len(item_to_idx),
            "train_samples": len(train_samples),
            "valid_samples": len(valid_samples),
            "train_invalid_rows": train_invalid_rows,
            "valid_invalid_rows": valid_invalid_rows,
        },
        "best": {
            "epoch": best_epoch,
            "valid_loss": best_valid_loss,
            "valid_auc": best_valid_auc,
            "checkpoint": str(best_checkpoint_path),
        },
        "final": {
            "train_loss": final_train_loss,
            "valid_loss": final_valid_loss,
            "checkpoint": str(last_checkpoint_path),
        },
        "history": history,
        "embeddings": {
            "user_embeddings": str(user_embedding_path),
            "item_embeddings": str(item_embedding_path),
            "user_index": str(user_index_path),
            "item_index": str(item_index_path),
        },
    }

    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(
        json.dumps(report_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return TwoTowerTrainingSummary(
        run_dir=str(run_dir),
        device=str(device),
        num_users=len(user_to_idx),
        num_items=len(item_to_idx),
        train_samples=len(train_samples),
        valid_samples=len(valid_samples),
        epochs=epochs,
        best_epoch=best_epoch,
        best_valid_loss=round(best_valid_loss, 8),
        best_valid_auc=round(best_valid_auc, 8),
        final_train_loss=round(final_train_loss, 8),
        final_valid_loss=round(final_valid_loss, 8),
        best_checkpoint_path=str(best_checkpoint_path),
        last_checkpoint_path=str(last_checkpoint_path),
        user_embedding_path=str(user_embedding_path),
        item_embedding_path=str(item_embedding_path),
        report_path=str(report_json),
    )


def summary_to_json(summary: TwoTowerTrainingSummary) -> str:
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2)
