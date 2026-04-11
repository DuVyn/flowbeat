"""Two-Tower P6：基于 embedding 生成每用户 TopK 推荐。"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import torch


@dataclass(slots=True)
class TwoTowerRankingSummary:
    """P6 排序构建摘要。"""

    total_users: int
    users_with_ranked_items: int
    average_ranked_items_per_user: float
    unique_recommended_songs: int
    top_k_items: int
    score_batch_size: int
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
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _resolve_device(device: str | None) -> torch.device:
    if device is None or device == "auto":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if device == "cuda" and not torch.cuda.is_available():
        return torch.device("cpu")
    return torch.device(device)


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
    """读取训练正样本，构建用户已交互物品索引集合。"""
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


def _score_user_batch(
    *,
    user_vectors: torch.Tensor,
    item_vectors_t: torch.Tensor,
) -> torch.Tensor:
    """批量计算用户向量与物品向量点积得分。"""
    return torch.matmul(user_vectors, item_vectors_t)


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
    device: str = "auto",
) -> TwoTowerRankingSummary:
    """基于 P4 导出的 embedding 生成 P6 的 user_topk_scored。"""
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
    item_embeddings_device = item_embeddings.to(runtime_device)
    item_embeddings_t = item_embeddings_device.transpose(0, 1).contiguous()

    # 0 号通常是 __UNK__，不参与推荐。
    unk_item_index = 0
    max_item_candidates = max(item_embeddings.shape[0] - 1, 1)
    effective_top_k = min(top_k_items, max_item_candidates)

    # 仅对真实用户（排除索引 0 的 __UNK__）进行推荐。
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
            score_matrix = _score_user_batch(
                user_vectors=user_tensor,
                item_vectors_t=item_embeddings_t,
            )

            if unk_item_index < score_matrix.shape[1]:
                score_matrix[:, unk_item_index] = float("-inf")

            # 屏蔽训练集中该用户已看过的正样本，降低“重复推荐已听歌曲”的概率。
            for row_offset, user_idx in enumerate(batch_user_indices):
                seen_set = seen_item_indices.get(user_idx)
                if not seen_set:
                    continue
                seen_tensor = torch.tensor(
                    sorted(seen_set),
                    device=runtime_device,
                    dtype=torch.long,
                )
                seen_tensor = seen_tensor[seen_tensor < score_matrix.shape[1]]
                if seen_tensor.numel() > 0:
                    score_matrix[row_offset, seen_tensor] = float("-inf")

            top_scores, top_indices = torch.topk(
                score_matrix,
                k=effective_top_k,
                dim=1,
                largest=True,
                sorted=True,
            )

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
        device=str(runtime_device),
        output_path=str(output_jsonl),
        meta_path=str(meta_path),
    )


def summary_to_json(summary: TwoTowerRankingSummary) -> str:
    """将构建摘要转为 JSON 字符串。"""
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2)
