"""双塔模型本地训练流程，支持断点续训与向量导出。"""

from __future__ import annotations

import json
import os
import random
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import torch
from torch import nn
from torch.utils.data import DataLoader, IterableDataset, get_worker_info

from models.two_tower.model import TwoTowerModel
from runtime_paths import to_posix_relative


@dataclass(slots=True)
class TwoTowerTrainingSummary:
    """单次训练运行目录的摘要信息。"""

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


class InteractionIterableDataset(IterableDataset[tuple[int, int, float]]):
    """从 jsonl 流式读取交互样本，避免一次性载入全部内存。"""

    def __init__(
        self,
        *,
        path: Path,
        user_to_idx: dict[str, int],
        item_to_idx: dict[str, int],
        max_rows: int | None,
        shuffle: bool,
        shuffle_buffer_size: int,
        seed: int,
    ) -> None:
        self.path = path
        self.user_to_idx = user_to_idx
        self.item_to_idx = item_to_idx
        self.max_rows = max_rows
        self.shuffle = shuffle
        self.shuffle_buffer_size = max(1, shuffle_buffer_size)
        self.seed = seed

    def _iter_samples(self):
        yielded = 0
        for row in _iter_jsonl(self.path):
            mapped = _map_row_to_sample(
                row=row,
                user_to_idx=self.user_to_idx,
                item_to_idx=self.item_to_idx,
                allow_extend_index=False,
            )
            if mapped is None:
                continue

            if self.max_rows is not None and yielded >= self.max_rows:
                break

            yielded += 1
            yield mapped

    def __iter__(self):
        worker_info = get_worker_info()
        worker_id = worker_info.id if worker_info else 0
        num_workers = worker_info.num_workers if worker_info else 1

        def _worker_samples():
            for sample_index, sample in enumerate(self._iter_samples()):
                if sample_index % num_workers != worker_id:
                    continue
                yield sample

        samples = _worker_samples()
        if not self.shuffle:
            for sample in samples:
                yield sample
            return

        rng = random.Random(self.seed + worker_id)
        buffer: list[tuple[int, int, float]] = []
        for sample in samples:
            buffer.append(sample)
            if len(buffer) < self.shuffle_buffer_size:
                continue

            pick = rng.randrange(len(buffer))
            yield buffer.pop(pick)

        while buffer:
            pick = rng.randrange(len(buffer))
            yield buffer.pop(pick)


def _set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _resolve_device(device: str | None) -> torch.device:
    normalized = (device or "auto").strip().lower()
    has_mps = bool(
        getattr(torch.backends, "mps", None)
        and torch.backends.mps.is_available()
        and torch.backends.mps.is_built()
    )

    if normalized == "auto":
        if torch.cuda.is_available():
            return torch.device("cuda")
        if has_mps:
            return torch.device("mps")
        return torch.device("cpu")

    if normalized == "cuda":
        if torch.cuda.is_available():
            return torch.device("cuda")
        warnings.warn("请求了 CUDA 但当前不可用，已回退到 CPU。", stacklevel=2)
        return torch.device("cpu")

    if normalized == "mps":
        if has_mps:
            return torch.device("mps")
        warnings.warn("请求了 MPS 但当前不可用，已回退到 CPU。", stacklevel=2)
        return torch.device("cpu")

    return torch.device(normalized)


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


def _to_bool(value: Any, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return _to_bool(value, default=default)


def _parse_optional_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None

    parsed = _to_int(value, default=0)
    if parsed == 0:
        return None
    return parsed


def _map_row_to_sample(
    *,
    row: dict[str, Any],
    user_to_idx: dict[str, int],
    item_to_idx: dict[str, int],
    allow_extend_index: bool,
) -> tuple[int, int, float] | None:
    user_key = str(row.get("user_key") or "").strip()
    song_id = str(row.get("song_id") or "").strip()
    if not user_key or not song_id:
        return None

    label_raw = _to_int(row.get("label"), default=0)
    label = 1.0 if label_raw > 0 else 0.0

    if allow_extend_index:
        user_idx = user_to_idx.setdefault(user_key, len(user_to_idx))
        item_idx = item_to_idx.setdefault(song_id, len(item_to_idx))
    else:
        user_idx = user_to_idx.get(user_key, 0)
        item_idx = item_to_idx.get(song_id, 0)

    return user_idx, item_idx, label


def _scan_interactions(
    *,
    path: Path,
    user_to_idx: dict[str, int],
    item_to_idx: dict[str, int],
    allow_extend_index: bool,
    max_rows: int | None,
) -> tuple[int, int]:
    """单次扫描样本文件，构建索引映射并统计有效/无效行数。"""
    valid_rows = 0
    invalid_rows = 0

    for row in _iter_jsonl(path):
        mapped = _map_row_to_sample(
            row=row,
            user_to_idx=user_to_idx,
            item_to_idx=item_to_idx,
            allow_extend_index=allow_extend_index,
        )
        if mapped is None:
            invalid_rows += 1
            continue

        if max_rows is not None and valid_rows >= max_rows:
            break

        valid_rows += 1

    return valid_rows, invalid_rows


def _binary_auc(labels: torch.Tensor, scores: torch.Tensor) -> float:
    """基于秩统计计算二分类 AUC。"""
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
    batch: Sequence[torch.Tensor],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    """将 DataLoader 返回的批次规范为三个张量。"""
    if len(batch) != 3:
        raise ValueError(f"期望 batch 为 3 个张量，实际为 {len(batch)} 个。")
    return batch[0], batch[1], batch[2]


def _evaluate_epoch(
    *,
    model: TwoTowerModel,
    dataloader: DataLoader,
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


def _capture_rng_state() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "python": random.getstate(),
        "torch": torch.get_rng_state(),
    }
    if torch.cuda.is_available():
        payload["cuda"] = torch.cuda.get_rng_state_all()
    return payload


def _restore_rng_state(payload: Any) -> None:
    if not isinstance(payload, dict):
        return

    python_state = payload.get("python")
    if python_state is not None:
        random.setstate(python_state)

    torch_state = payload.get("torch")
    if isinstance(torch_state, torch.Tensor):
        torch.set_rng_state(torch_state)

    cuda_state = payload.get("cuda")
    if torch.cuda.is_available() and isinstance(cuda_state, list):
        torch.cuda.set_rng_state_all(cuda_state)


def _resolve_resume_checkpoint(run_dir: Path, resume_from: str) -> Path:
    checkpoints_dir = run_dir / "checkpoints"
    resume_value = resume_from.strip().lower()
    if resume_value in {"", "last"}:
        return checkpoints_dir / "last_model.pt"
    if resume_value == "best":
        return checkpoints_dir / "best_model.pt"

    user_path = Path(resume_from).expanduser()
    if user_path.is_absolute():
        return user_path.resolve()
    return (run_dir / user_path).resolve()


def _worker_init_factory(seed: int):
    def _worker_init(worker_id: int) -> None:
        worker_seed = seed + worker_id
        random.seed(worker_seed)
        torch.manual_seed(worker_seed)

    return _worker_init


def _resolve_dataloader_options(
    *,
    training_config: dict[str, Any],
    device: torch.device,
    seed: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    cpu_count = os.cpu_count() or 1
    default_num_workers = max(min(cpu_count // 2, 8), 0)

    num_workers = int(training_config.get("num_workers", default_num_workers))
    num_workers = max(0, _env_int("FLOWBEAT_TT_NUM_WORKERS", num_workers))

    default_pin_memory = device.type == "cuda"
    pin_memory = _to_bool(training_config.get("pin_memory"), default_pin_memory)
    pin_memory = _env_bool("FLOWBEAT_TT_PIN_MEMORY", pin_memory)
    if device.type != "cuda":
        pin_memory = False

    default_persistent_workers = num_workers > 0
    persistent_workers = _to_bool(
        training_config.get("persistent_workers"),
        default_persistent_workers,
    )
    persistent_workers = _env_bool(
        "FLOWBEAT_TT_PERSISTENT_WORKERS",
        persistent_workers,
    )
    if num_workers <= 0:
        persistent_workers = False

    prefetch_factor = training_config.get("prefetch_factor")
    if prefetch_factor is None:
        prefetch_factor = 2
    prefetch_factor = _env_int("FLOWBEAT_TT_PREFETCH_FACTOR", int(prefetch_factor))
    if num_workers <= 0:
        prefetch_factor = None
    else:
        prefetch_factor = max(1, int(prefetch_factor))

    options: dict[str, Any] = {
        "num_workers": num_workers,
        "pin_memory": pin_memory,
        "persistent_workers": persistent_workers,
    }
    if prefetch_factor is not None:
        options["prefetch_factor"] = prefetch_factor
    if num_workers > 0:
        options["worker_init_fn"] = _worker_init_factory(seed)

    summary = {
        "num_workers": num_workers,
        "pin_memory": pin_memory,
        "persistent_workers": persistent_workers,
        "prefetch_factor": prefetch_factor,
    }
    return options, summary


def _build_checkpoint_payload(
    *,
    epoch: int,
    model: TwoTowerModel,
    optimizer: torch.optim.Optimizer,
    user_to_idx: dict[str, int],
    item_to_idx: dict[str, int],
    history: list[dict[str, Any]],
    best_epoch: int,
    best_valid_loss: float,
    best_valid_auc: float,
    dataloader_settings: dict[str, Any],
) -> dict[str, Any]:
    return {
        "epoch": epoch,
        "model_state_dict": model.state_dict(),
        "optimizer_state_dict": optimizer.state_dict(),
        "user_to_idx": user_to_idx,
        "item_to_idx": item_to_idx,
        "history": history,
        "best_epoch": best_epoch,
        "best_valid_loss": best_valid_loss,
        "best_valid_auc": best_valid_auc,
        "rng_state": _capture_rng_state(),
        "dataloader": dataloader_settings,
    }


def train_two_tower_local_mvp(
    *,
    interactions_train_jsonl: Path,
    interactions_valid_jsonl: Path,
    run_dir: Path,
    report_json: Path,
    training_config: dict[str, Any],
    seed: int,
) -> TwoTowerTrainingSummary:
    """训练双塔模型并导出检查点与向量产物。"""
    _set_seed(seed)

    embedding_dim = int(training_config.get("embedding_dim", 64))
    hidden_dims = [int(dim) for dim in training_config.get("hidden_dims") or [128, 64]]
    dropout = float(training_config.get("dropout", 0.1))
    batch_size = int(training_config.get("batch_size", 256))
    epochs = int(training_config.get("epochs", 3))
    learning_rate = float(training_config.get("learning_rate", 1e-3))
    weight_decay = float(training_config.get("weight_decay", 1e-5))
    requested_device = str(training_config.get("device", "auto"))

    max_rows_per_epoch_cfg = training_config.get("max_rows_per_epoch")
    max_rows_per_epoch = _parse_optional_int(max_rows_per_epoch_cfg)
    valid_max_rows_cfg = training_config.get("valid_max_rows_per_epoch")
    valid_max_rows = _parse_optional_int(valid_max_rows_cfg)
    if valid_max_rows is None:
        valid_max_rows = max_rows_per_epoch

    shuffle_buffer_size = int(training_config.get("shuffle_buffer_size", 20_000))
    shuffle_buffer_size = max(1, shuffle_buffer_size)

    resume = _to_bool(training_config.get("resume"), default=False)
    resume_from = str(training_config.get("resume_from") or "last")

    if batch_size <= 0:
        raise ValueError("batch_size 必须 > 0")
    if epochs <= 0:
        raise ValueError("epochs 必须 > 0")

    device = _resolve_device(requested_device)
    loader_options, loader_settings_summary = _resolve_dataloader_options(
        training_config=training_config,
        device=device,
        seed=seed,
    )

    user_to_idx: dict[str, int] = {"__UNK__": 0}
    item_to_idx: dict[str, int] = {"__UNK__": 0}

    train_samples, train_invalid_rows = _scan_interactions(
        path=interactions_train_jsonl,
        user_to_idx=user_to_idx,
        item_to_idx=item_to_idx,
        allow_extend_index=True,
        max_rows=max_rows_per_epoch,
    )
    valid_samples, valid_invalid_rows = _scan_interactions(
        path=interactions_valid_jsonl,
        user_to_idx=user_to_idx,
        item_to_idx=item_to_idx,
        allow_extend_index=False,
        max_rows=valid_max_rows,
    )

    if train_samples <= 0:
        raise ValueError("训练集为空，无法执行训练。")
    if valid_samples <= 0:
        raise ValueError("验证集为空，无法执行训练。")

    train_dataset = InteractionIterableDataset(
        path=interactions_train_jsonl,
        user_to_idx=user_to_idx,
        item_to_idx=item_to_idx,
        max_rows=max_rows_per_epoch,
        shuffle=True,
        shuffle_buffer_size=shuffle_buffer_size,
        seed=seed,
    )
    valid_dataset = InteractionIterableDataset(
        path=interactions_valid_jsonl,
        user_to_idx=user_to_idx,
        item_to_idx=item_to_idx,
        max_rows=valid_max_rows,
        shuffle=False,
        shuffle_buffer_size=shuffle_buffer_size,
        seed=seed,
    )

    train_loader = DataLoader(train_dataset, batch_size=batch_size, **loader_options)
    valid_loader = DataLoader(valid_dataset, batch_size=batch_size, **loader_options)

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
    start_epoch = 1

    if resume:
        resume_checkpoint = _resolve_resume_checkpoint(run_dir, resume_from)
        if not resume_checkpoint.exists():
            raise FileNotFoundError(
                f"断点续训失败，checkpoint 不存在: {resume_checkpoint}"
            )

        checkpoint = torch.load(resume_checkpoint, map_location="cpu")
        checkpoint_user_to_idx = checkpoint.get("user_to_idx")
        checkpoint_item_to_idx = checkpoint.get("item_to_idx")
        if (
            checkpoint_user_to_idx != user_to_idx
            or checkpoint_item_to_idx != item_to_idx
        ):
            raise RuntimeError(
                "断点续训失败：当前样本映射与 checkpoint 不一致，请确认输入数据与配置未变化。"
            )

        model.load_state_dict(checkpoint["model_state_dict"])
        optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

        restored_epoch = int(checkpoint.get("epoch", 0))
        start_epoch = max(1, restored_epoch + 1)

        best_epoch = int(checkpoint.get("best_epoch", restored_epoch))
        best_valid_loss = float(
            checkpoint.get(
                "best_valid_loss", checkpoint.get("valid_loss", best_valid_loss)
            )
        )
        best_valid_auc = float(
            checkpoint.get(
                "best_valid_auc", checkpoint.get("valid_auc", best_valid_auc)
            )
        )

        loaded_history = checkpoint.get("history")
        if isinstance(loaded_history, list):
            history = loaded_history
            if history:
                last_history = history[-1]
                final_train_loss = float(
                    last_history.get("train_loss", final_train_loss)
                )
                final_valid_loss = float(
                    last_history.get("valid_loss", final_valid_loss)
                )

        _restore_rng_state(checkpoint.get("rng_state"))

    for epoch in range(start_epoch, epochs + 1):
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

        checkpoint_payload = _build_checkpoint_payload(
            epoch=epoch,
            model=model,
            optimizer=optimizer,
            user_to_idx=user_to_idx,
            item_to_idx=item_to_idx,
            history=history,
            best_epoch=best_epoch,
            best_valid_loss=best_valid_loss,
            best_valid_auc=best_valid_auc,
            dataloader_settings=loader_settings_summary,
        )
        torch.save(checkpoint_payload, last_checkpoint_path)

        if epoch == best_epoch:
            torch.save(checkpoint_payload, best_checkpoint_path)

    if start_epoch > epochs:
        final_valid_loss, _ = _evaluate_epoch(
            model=model,
            dataloader=valid_loader,
            criterion=criterion,
            device=device,
        )

    if not last_checkpoint_path.exists():
        checkpoint_payload = _build_checkpoint_payload(
            epoch=max(epochs, start_epoch - 1),
            model=model,
            optimizer=optimizer,
            user_to_idx=user_to_idx,
            item_to_idx=item_to_idx,
            history=history,
            best_epoch=best_epoch,
            best_valid_loss=best_valid_loss,
            best_valid_auc=best_valid_auc,
            dataloader_settings=loader_settings_summary,
        )
        torch.save(checkpoint_payload, last_checkpoint_path)

    if not best_checkpoint_path.exists():
        torch.save(
            torch.load(last_checkpoint_path, map_location="cpu"), best_checkpoint_path
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
        "run_id": run_dir.name,
        "run_dir": run_dir.resolve().as_posix(),
        "artifacts": {
            "run_dir": run_dir.resolve().as_posix(),
        },
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
            "resume": resume,
            "resume_from": resume_from,
            "max_rows_per_epoch": max_rows_per_epoch,
            "valid_max_rows_per_epoch": valid_max_rows,
            "shuffle_buffer_size": shuffle_buffer_size,
            "dataloader": loader_settings_summary,
        },
        "inputs": {
            "interactions_train_jsonl": interactions_train_jsonl.resolve().as_posix(),
            "interactions_valid_jsonl": interactions_valid_jsonl.resolve().as_posix(),
        },
        "data_summary": {
            "num_users": len(user_to_idx),
            "num_items": len(item_to_idx),
            "train_samples": train_samples,
            "valid_samples": valid_samples,
            "train_invalid_rows": train_invalid_rows,
            "valid_invalid_rows": valid_invalid_rows,
        },
        "best": {
            "epoch": best_epoch,
            "valid_loss": best_valid_loss,
            "valid_auc": best_valid_auc,
            "checkpoint": to_posix_relative(best_checkpoint_path, base_dir=run_dir),
        },
        "final": {
            "train_loss": final_train_loss,
            "valid_loss": final_valid_loss,
            "checkpoint": to_posix_relative(last_checkpoint_path, base_dir=run_dir),
        },
        "history": history,
        "embeddings": {
            "user_embeddings": to_posix_relative(user_embedding_path, base_dir=run_dir),
            "item_embeddings": to_posix_relative(item_embedding_path, base_dir=run_dir),
            "user_index": to_posix_relative(user_index_path, base_dir=run_dir),
            "item_index": to_posix_relative(item_index_path, base_dir=run_dir),
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
        train_samples=train_samples,
        valid_samples=valid_samples,
        epochs=epochs,
        best_epoch=best_epoch,
        best_valid_loss=round(float(best_valid_loss), 8),
        best_valid_auc=round(float(best_valid_auc), 8),
        final_train_loss=round(float(final_train_loss), 8),
        final_valid_loss=round(float(final_valid_loss), 8),
        best_checkpoint_path=str(best_checkpoint_path),
        last_checkpoint_path=str(last_checkpoint_path),
        user_embedding_path=str(user_embedding_path),
        item_embedding_path=str(item_embedding_path),
        report_path=str(report_json),
    )


def summary_to_json(summary: TwoTowerTrainingSummary) -> str:
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2)
