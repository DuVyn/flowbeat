"""双塔排序模块：基于导出的向量生成用户 TopK 推荐。"""

from __future__ import annotations

import json
import math
import warnings
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import torch


@dataclass(slots=True)
class TwoTowerRankingSummary:
    """单次推理执行的排序摘要。"""

    total_users: int
    users_with_ranked_items: int
    average_ranked_items_per_user: float
    unique_recommended_songs: int
    top_k_items: int
    score_batch_size: int
    item_block_size: int
    device: str
    output_path: str
    meta_path: str


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            yield json.loads(text)


def _to_int(value: object, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return int(text)
        except ValueError:
            return default
    return default


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
        warnings.warn("请求了 CUDA 但不可用，已回退到 CPU。", stacklevel=2)
        return torch.device("cpu")

    if normalized == "mps":
        if has_mps:
            return torch.device("mps")
        warnings.warn("请求了 MPS 但不可用，已回退到 CPU。", stacklevel=2)
        return torch.device("cpu")

    return torch.device(normalized)


def _load_index_map(path: Path) -> dict[str, int]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"索引文件格式错误: {path}")
    mapping: dict[str, int] = {}
    for key, value in raw.items():
        idx = _to_int(value, default=-1)
        if idx < 0:
            continue
        mapping[str(key)] = idx
    return mapping


def _build_reverse_index(index_map: dict[str, int], size: int) -> list[str]:
    reverse = [""] * size
    for key, idx in index_map.items():
        if 0 <= idx < size:
            reverse[idx] = key
    return reverse


def _load_positive_seen_item_indices(
    *,
    interactions_train_jsonl: Path,
    user_to_idx: dict[str, int],
    item_to_idx: dict[str, int],
) -> dict[int, set[int]]:
    """读取训练集中用户正样本物品索引，用于抑制重复推荐。"""
    seen: dict[int, set[int]] = {}
    for row in _iter_jsonl(interactions_train_jsonl):
        if _to_int(row.get("label"), default=0) <= 0:
            continue

        user_key = str(row.get("user_key") or "").strip()
        song_id = str(row.get("song_id") or "").strip()
        if not user_key or not song_id:
            continue

        user_idx = user_to_idx.get(user_key)
        item_idx = item_to_idx.get(song_id)
        if user_idx is None or item_idx is None:
            continue

        user_seen = seen.setdefault(user_idx, set())
        user_seen.add(item_idx)

    return seen


def _select_safe_item_block_size(
    *,
    requested_item_block_size: int,
    embedding_dim: int,
    runtime_device: torch.device,
) -> int:
    if requested_item_block_size <= 0:
        raise ValueError("item_block_size 必须大于 0")

    if runtime_device.type != "cuda":
        return requested_item_block_size

    try:
        device_properties = torch.cuda.get_device_properties(runtime_device)
    except Exception:
        return requested_item_block_size

    total_memory = int(device_properties.total_memory)
    bytes_per_item = max(embedding_dim, 1) * 4
    safe_limit = max(int((total_memory * 0.35) // bytes_per_item), 1)
    adjusted = min(requested_item_block_size, safe_limit)

    if adjusted < requested_item_block_size:
        warnings.warn(
            "item_block_size 已根据显存自动下调，避免打分阶段 OOM。"
            f" requested={requested_item_block_size}, adjusted={adjusted}",
            stacklevel=2,
        )
    return adjusted


def _score_user_batch_blockwise(
    *,
    user_vectors: torch.Tensor,
    item_embeddings: torch.Tensor,
    batch_user_indices: list[int],
    seen_item_indices: dict[int, set[int]],
    effective_top_k: int,
    item_block_size: int,
    runtime_device: torch.device,
    unk_item_index: int,
) -> tuple[torch.Tensor, torch.Tensor]:
    batch_size = user_vectors.shape[0]
    best_scores = torch.full(
        (batch_size, effective_top_k),
        fill_value=float("-inf"),
        device=runtime_device,
        dtype=torch.float32,
    )
    best_indices = torch.full(
        (batch_size, effective_top_k),
        fill_value=-1,
        device=runtime_device,
        dtype=torch.long,
    )

    total_items = item_embeddings.shape[0]
    for block_start in range(0, total_items, item_block_size):
        block_end = min(block_start + item_block_size, total_items)
        item_block = item_embeddings[block_start:block_end].to(runtime_device)
        block_scores = torch.matmul(user_vectors, item_block.transpose(0, 1))

        if block_start <= unk_item_index < block_end:
            block_scores[:, unk_item_index - block_start] = float("-inf")

        for row_offset, user_idx in enumerate(batch_user_indices):
            seen_set = seen_item_indices.get(user_idx)
            if not seen_set:
                continue

            local_seen = [
                item_idx - block_start
                for item_idx in seen_set
                if block_start <= item_idx < block_end
            ]
            if not local_seen:
                continue

            seen_tensor = torch.tensor(
                local_seen, device=runtime_device, dtype=torch.long
            )
            block_scores[row_offset, seen_tensor] = float("-inf")

        block_k = min(effective_top_k, block_end - block_start)
        block_top_scores, block_top_local_indices = torch.topk(
            block_scores,
            k=block_k,
            dim=1,
            largest=True,
            sorted=True,
        )
        block_top_indices = block_top_local_indices + block_start

        merged_scores = torch.cat([best_scores, block_top_scores], dim=1)
        merged_indices = torch.cat([best_indices, block_top_indices], dim=1)

        best_scores, best_positions = torch.topk(
            merged_scores,
            k=effective_top_k,
            dim=1,
            largest=True,
            sorted=True,
        )
        best_indices = torch.gather(merged_indices, 1, best_positions)

    return best_scores, best_indices


def build_two_tower_topk_from_embeddings(
    *,
    user_embedding_path: Path,
    item_embedding_path: Path,
    user_index_json: Path,
    item_index_json: Path,
    interactions_train_jsonl: Path,
    output_jsonl: Path,
    top_k_items: int = 100,
    score_batch_size: int = 64,
    item_block_size: int = 20_000,
    device: str = "auto",
) -> TwoTowerRankingSummary:
    """基于训练导出的向量生成用户 TopK 推荐结果。"""
    if top_k_items <= 0:
        raise ValueError("top_k_items 必须大于 0")
    if score_batch_size <= 0:
        raise ValueError("score_batch_size 必须大于 0")

    user_embeddings = torch.load(user_embedding_path, map_location="cpu")
    item_embeddings = torch.load(item_embedding_path, map_location="cpu")
    if not isinstance(user_embeddings, torch.Tensor) or not isinstance(
        item_embeddings, torch.Tensor
    ):
        raise ValueError("embedding 文件格式错误，必须为 Tensor")

    user_embeddings = user_embeddings.detach().to(dtype=torch.float32)
    item_embeddings = item_embeddings.detach().to(dtype=torch.float32)

    user_to_idx = _load_index_map(user_index_json)
    item_to_idx = _load_index_map(item_index_json)

    if user_embeddings.shape[0] <= 1 or item_embeddings.shape[0] <= 1:
        raise ValueError("embedding 数量不足，无法执行 TopK 生成")

    reverse_user = _build_reverse_index(user_to_idx, size=user_embeddings.shape[0])
    reverse_item = _build_reverse_index(item_to_idx, size=item_embeddings.shape[0])

    seen_item_indices = _load_positive_seen_item_indices(
        interactions_train_jsonl=interactions_train_jsonl,
        user_to_idx=user_to_idx,
        item_to_idx=item_to_idx,
    )

    runtime_device = _resolve_device(device)
    item_block_size = _select_safe_item_block_size(
        requested_item_block_size=item_block_size,
        embedding_dim=int(item_embeddings.shape[1]),
        runtime_device=runtime_device,
    )

    # 索引 0 通常是 __UNK__，不应进入推荐结果。
    unk_item_index = 0
    max_item_candidates = max(item_embeddings.shape[0] - 1, 1)
    effective_top_k = min(top_k_items, max_item_candidates)

    # 仅对真实用户做推荐（排除 __UNK__ 索引 0）。
    user_indices = [
        idx
        for idx in sorted(user_to_idx.values())
        if 0 < idx < user_embeddings.shape[0] and reverse_user[idx]
    ]

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    total_users = 0
    users_with_ranked_items = 0
    total_ranked_items = 0
    unique_recommended_songs: set[str] = set()

    with output_jsonl.open("w", encoding="utf-8") as out_file:
        for batch_start in range(0, len(user_indices), score_batch_size):
            batch_user_indices = user_indices[
                batch_start : batch_start + score_batch_size
            ]
            if not batch_user_indices:
                continue

            user_tensor = user_embeddings[batch_user_indices].to(runtime_device)
            try:
                top_scores, top_indices = _score_user_batch_blockwise(
                    user_vectors=user_tensor,
                    item_embeddings=item_embeddings,
                    batch_user_indices=batch_user_indices,
                    seen_item_indices=seen_item_indices,
                    effective_top_k=effective_top_k,
                    item_block_size=item_block_size,
                    runtime_device=runtime_device,
                    unk_item_index=unk_item_index,
                )
            except RuntimeError as exc:
                error_text = str(exc).lower()
                if runtime_device.type == "cuda" and "out of memory" in error_text:
                    warnings.warn(
                        "CUDA 显存不足，已回退到 CPU 继续完成推理。",
                        stacklevel=2,
                    )
                    torch.cuda.empty_cache()
                    runtime_device = torch.device("cpu")
                    user_tensor = user_embeddings[batch_user_indices].to(runtime_device)
                    top_scores, top_indices = _score_user_batch_blockwise(
                        user_vectors=user_tensor,
                        item_embeddings=item_embeddings,
                        batch_user_indices=batch_user_indices,
                        seen_item_indices=seen_item_indices,
                        effective_top_k=effective_top_k,
                        item_block_size=item_block_size,
                        runtime_device=runtime_device,
                        unk_item_index=unk_item_index,
                    )
                else:
                    raise

            top_scores_cpu = top_scores.detach().cpu()
            top_indices_cpu = top_indices.detach().cpu()

            for row_offset, user_idx in enumerate(batch_user_indices):
                total_users += 1
                user_key = reverse_user[user_idx]

                items: list[dict[str, object]] = []
                for rank_offset, item_idx in enumerate(
                    top_indices_cpu[row_offset].tolist()
                ):
                    score_value = float(top_scores_cpu[row_offset][rank_offset].item())
                    if item_idx < 0:
                        continue
                    if not math.isfinite(score_value):
                        continue

                    if not (0 <= item_idx < len(reverse_item)):
                        continue
                    song_id = reverse_item[item_idx]
                    if not song_id or song_id == "__UNK__":
                        continue

                    unique_recommended_songs.add(song_id)
                    items.append(
                        {
                            "song_id": song_id,
                            "rank": len(items) + 1,
                            "score": round(score_value, 6),
                            "reason": "two_tower_embedding_match",
                        }
                    )
                    if len(items) >= top_k_items:
                        break

                if items:
                    users_with_ranked_items += 1
                total_ranked_items += len(items)

                row = {
                    "user_key": user_key,
                    "user_key_type": "msno",
                    "strategy": "two_tower",
                    "ranked_count": len(items),
                    "items": items,
                }
                out_file.write(json.dumps(row, ensure_ascii=False) + "\n")

    average_ranked_items_per_user = (
        total_ranked_items / total_users if total_users > 0 else 0.0
    )

    meta_path = output_jsonl.with_suffix(".meta.json")
    meta_payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "user_embedding_path": str(user_embedding_path),
            "item_embedding_path": str(item_embedding_path),
            "user_index_json": str(user_index_json),
            "item_index_json": str(item_index_json),
            "interactions_train_jsonl": str(interactions_train_jsonl),
        },
        "settings": {
            "top_k_items": top_k_items,
            "score_batch_size": score_batch_size,
            "item_block_size": item_block_size,
            "device": str(runtime_device),
        },
        "summary": {
            "total_users": total_users,
            "users_with_ranked_items": users_with_ranked_items,
            "average_ranked_items_per_user": round(
                average_ranked_items_per_user,
                6,
            ),
            "unique_recommended_songs": len(unique_recommended_songs),
        },
    }
    meta_path.write_text(
        json.dumps(meta_payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return TwoTowerRankingSummary(
        total_users=total_users,
        users_with_ranked_items=users_with_ranked_items,
        average_ranked_items_per_user=round(average_ranked_items_per_user, 6),
        unique_recommended_songs=len(unique_recommended_songs),
        top_k_items=top_k_items,
        score_batch_size=score_batch_size,
        item_block_size=item_block_size,
        device=str(runtime_device),
        output_path=str(output_jsonl),
        meta_path=str(meta_path),
    )


def summary_to_json(summary: TwoTowerRankingSummary) -> str:
    """将排序摘要序列化为 JSON 字符串。"""
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2)
