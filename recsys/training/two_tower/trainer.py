"""训练循环控制器：封装 epoch 级训练、验证、checkpoint、早停与向量导出。"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import torch
from torch import nn
from torch.utils.data import DataLoader

from models.two_tower.model import TwoTowerModel
from training.two_tower.config_schema import TrainParams
from training.two_tower.storage_backend import StorageBackend


@dataclass(slots=True)
class TrainResult:
    """训练结果摘要。"""
    run_dir: str
    device: str
    num_users: int
    num_items: int
    train_samples: int
    test_samples: int
    total_epochs: int
    best_epoch: int
    best_test_loss: float
    best_test_auc: float
    final_train_loss: float
    final_test_loss: float


def _log(msg: str) -> None:
    print(f"[Trainer] {msg}", flush=True)


def _set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _binary_auc(labels: torch.Tensor, scores: torch.Tensor) -> float:
    if labels.numel() == 0:
        return 0.5
    pos_mask = labels > 0.5
    pos_n = int(pos_mask.sum().item())
    neg_n = int((~pos_mask).sum().item())
    if pos_n == 0 or neg_n == 0:
        return 0.5
    order = torch.argsort(scores)
    ranks = torch.empty_like(order, dtype=torch.float32)
    ranks[order] = torch.arange(1, order.numel() + 1, dtype=torch.float32, device=scores.device)
    return float((ranks[pos_mask].sum().item() - pos_n * (pos_n + 1) / 2) / (pos_n * neg_n))


@torch.no_grad()
def _evaluate(model: TwoTowerModel, loader: DataLoader, criterion: nn.Module, device: torch.device):
    model.eval()
    total_loss, total_n = 0.0, 0
    all_scores, all_labels = [], []
    for batch in loader:
        u, i, l = batch[0].to(device), batch[1].to(device), batch[2].to(device)
        logits = model(u, i)
        loss = criterion(logits, l)
        n = l.shape[0]
        total_loss += loss.item() * n
        total_n += n
        all_scores.append(logits.detach())
        all_labels.append(l.detach())
    avg_loss = total_loss / max(1, total_n)
    scores = torch.cat(all_scores) if all_scores else torch.tensor([])
    labels = torch.cat(all_labels) if all_labels else torch.tensor([])
    auc = _binary_auc(labels, scores)
    return avg_loss, auc


def _resolve_ckpt_path(checkpoint_dir: str, resume_from: str) -> str:
    rf = resume_from.strip().lower()
    if rf in ("", "last"):
        return checkpoint_dir.rstrip("/") + "/last_model.pt"
    if rf == "best":
        return checkpoint_dir.rstrip("/") + "/best_model.pt"
    return resume_from


def train(
    *,
    model: TwoTowerModel,
    train_loader: DataLoader,
    test_loader: DataLoader,
    train_params: TrainParams,
    backend: StorageBackend,
    checkpoint_dir: str,
    embedding_dir: str,
    report_dir: str,
    user_to_idx: dict[int, int],
    item_to_idx: dict[int, int],
    num_users: int,
    num_items: int,
    seed: int,
    device: torch.device,
) -> TrainResult:
    """执行完整的训练循环。"""
    _set_seed(seed)

    model = model.to(device)
    criterion = nn.BCEWithLogitsLoss()
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=train_params.learning_rate,
        weight_decay=train_params.weight_decay,
    )

    epochs = train_params.epochs
    log_every = train_params.log_every_steps
    patience = train_params.early_stopping_patience

    best_ckpt = checkpoint_dir.rstrip("/") + "/best_model.pt"
    last_ckpt = checkpoint_dir.rstrip("/") + "/last_model.pt"

    backend.makedirs(checkpoint_dir)
    backend.makedirs(embedding_dir)
    backend.makedirs(report_dir)

    best_epoch, best_loss, best_auc = 0, float("inf"), 0.0
    final_train_loss, final_test_loss = 0.0, 0.0
    history: list[dict[str, Any]] = []
    start_epoch = 1
    patience_counter = 0

    # 断点续训
    if train_params.resume:
        resume_path = _resolve_ckpt_path(checkpoint_dir, train_params.resume_from)
        if backend.exists(resume_path):
            _log(f"加载 checkpoint: {resume_path}")
            ckpt = backend.load_checkpoint(resume_path)
            model.load_state_dict(ckpt["model_state_dict"])
            optimizer.load_state_dict(ckpt["optimizer_state_dict"])
            start_epoch = int(ckpt.get("epoch", 0)) + 1
            best_epoch = int(ckpt.get("best_epoch", 0))
            best_loss = float(ckpt.get("best_test_loss", float("inf")))
            best_auc = float(ckpt.get("best_test_auc", 0.0))
            history = ckpt.get("history", [])
            _log(f"从 epoch {start_epoch} 继续训练")
        else:
            _log(f"未找到 checkpoint ({resume_path})，从头开始训练")

    train_samples = len(train_loader.dataset)
    test_samples = len(test_loader.dataset)
    est_steps = max(1, math.ceil(train_samples / train_params.batch_size))

    _log(
        f"训练参数: epochs={epochs}, batch={train_params.batch_size}, "
        f"lr={train_params.learning_rate}, device={device}, "
        f"train={train_samples}, test={test_samples}"
    )

    for epoch in range(start_epoch, epochs + 1):
        t0 = time.perf_counter()
        model.train()
        loss_sum, n_sum, step = 0.0, 0, 0

        for step, batch in enumerate(train_loader, 1):
            u = batch[0].to(device)
            i = batch[1].to(device)
            l = batch[2].to(device)

            optimizer.zero_grad(set_to_none=True)
            logits = model(u, i)
            loss = criterion(logits, l)
            loss.backward()
            optimizer.step()

            bs = l.shape[0]
            loss_sum += loss.item() * bs
            n_sum += bs

            if step == 1 or step % log_every == 0:
                rl = loss_sum / max(1, n_sum)
                pct = n_sum / train_samples * 100
                _log(f"[Epoch {epoch}/{epochs}] step={step}/{est_steps} ({pct:.1f}%) loss={rl:.6f}")

        final_train_loss = loss_sum / max(1, n_sum)
        test_loss, test_auc = _evaluate(model, test_loader, criterion, device)
        final_test_loss = test_loss
        cost = time.perf_counter() - t0

        history.append({
            "epoch": epoch,
            "train_loss": round(final_train_loss, 8),
            "test_loss": round(test_loss, 8),
            "test_auc": round(test_auc, 8),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        improved = test_loss < best_loss
        if improved:
            best_loss, best_auc, best_epoch = test_loss, test_auc, epoch
            patience_counter = 0
            _log(f"[Epoch {epoch}] ★ 新最优: loss={best_loss:.6f}, auc={best_auc:.6f}")
        else:
            patience_counter += 1

        # 保存 checkpoint
        payload = {
            "epoch": epoch,
            "model_state_dict": model.state_dict(),
            "optimizer_state_dict": optimizer.state_dict(),
            "user_to_idx": user_to_idx,
            "item_to_idx": item_to_idx,
            "best_epoch": best_epoch,
            "best_test_loss": best_loss,
            "best_test_auc": best_auc,
            "history": history,
        }
        backend.save_checkpoint(payload, last_ckpt)
        if improved:
            backend.save_checkpoint(payload, best_ckpt)

        _log(
            f"[Epoch {epoch}/{epochs}] train_loss={final_train_loss:.6f} "
            f"test_loss={test_loss:.6f} auc={test_auc:.6f} ({cost:.1f}s)"
        )

        # 早停
        if patience > 0 and patience_counter >= patience:
            _log(f"早停触发: 连续 {patience} 个 epoch 无改善")
            break

    # 导出向量
    _log("导出 embedding 向量...")
    model.eval()
    with torch.no_grad():
        u_ids = torch.arange(num_users, device=device, dtype=torch.long)
        i_ids = torch.arange(num_items, device=device, dtype=torch.long)
        u_emb = model.encode_user(u_ids).cpu()
        i_emb = model.encode_item(i_ids).cpu()

    backend.save_tensor(u_emb, embedding_dir.rstrip("/") + "/user_embeddings.pt")
    backend.save_tensor(i_emb, embedding_dir.rstrip("/") + "/item_embeddings.pt")
    backend.save_json(user_to_idx, embedding_dir.rstrip("/") + "/user_index.json")
    backend.save_json(item_to_idx, embedding_dir.rstrip("/") + "/item_index.json")

    # 写入训练报告
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "num_users": num_users,
        "num_items": num_items,
        "train_samples": train_samples,
        "test_samples": test_samples,
        "best": {"epoch": best_epoch, "test_loss": best_loss, "test_auc": best_auc},
        "final": {"train_loss": final_train_loss, "test_loss": final_test_loss},
        "history": history,
    }
    backend.save_json(report, report_dir.rstrip("/") + "/training_report.json")
    _log("训练完成")

    return TrainResult(
        run_dir=checkpoint_dir,
        device=str(device),
        num_users=num_users,
        num_items=num_items,
        train_samples=train_samples,
        test_samples=test_samples,
        total_epochs=len(history),
        best_epoch=best_epoch,
        best_test_loss=round(best_loss, 8),
        best_test_auc=round(best_auc, 8),
        final_train_loss=round(final_train_loss, 8),
        final_test_loss=round(final_test_loss, 8),
    )
