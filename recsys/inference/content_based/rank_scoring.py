"""Content-Based 规则打分层。

输入：
- user_candidate_set.jsonl（候选召回产物）
- song_content_profile.jsonl（歌曲画像产物）

输出：
- user_topk_scored.jsonl
- user_topk_scored.meta.json
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class RankingBuildSummary:
    """打分构建摘要。"""

    total_users: int
    users_with_candidates: int
    users_with_ranked_items: int
    average_ranked_items_per_user: float
    unique_candidate_songs: int
    missing_song_feature_count: int
    top_k_items: int
    output_path: str
    meta_path: str


def _iter_jsonl(path: Path):
    """按行读取 JSONL，返回字典对象。"""
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            yield json.loads(text)


def _to_float(value: object, default: float = 0.0) -> float:
    if isinstance(value, bool):
        return float(value)
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return default
        try:
            return float(text)
        except ValueError:
            return default
    return default


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


def _collect_candidate_song_ids(candidate_jsonl: Path) -> set[str]:
    """扫描候选文件，收集候选歌曲 ID 集合。"""
    song_ids: set[str] = set()
    for row in _iter_jsonl(candidate_jsonl):
        candidates = row.get("candidates") or []
        if not isinstance(candidates, list):
            continue
        for item in candidates:
            song_id = str(item.get("song_id") or "").strip()
            if song_id:
                song_ids.add(song_id)
    return song_ids


def _build_song_feature_index(
    *,
    song_profile_jsonl: Path,
    target_song_ids: set[str],
) -> dict[str, dict[str, object]]:
    """仅为候选歌曲构建特征索引，避免加载全量歌曲画像。"""
    index: dict[str, dict[str, object]] = {}

    for row in _iter_jsonl(song_profile_jsonl):
        song_id = str(row.get("song_id") or "").strip()
        if not song_id or song_id not in target_song_ids:
            continue

        genre_codes_raw = row.get("genre_codes") or []
        genre_codes = {
            str(code).strip() for code in genre_codes_raw if str(code).strip()
        }
        index[song_id] = {
            "artist_name": str(row.get("artist_name") or "").strip(),
            "popularity_score": _to_float(row.get("popularity_score"), default=0.0),
            "genre_codes": genre_codes,
            "language": row.get("language"),
        }

    return index


def _build_reason(
    *,
    genre_overlap_count: int,
    popularity_score: float,
    match_count: int,
) -> str:
    """生成可解释的规则原因标签。"""
    if genre_overlap_count >= 2:
        return "multi_genre_match"
    if genre_overlap_count == 1 and popularity_score >= 0.7:
        return "genre_match_popular"
    if genre_overlap_count == 1:
        return "genre_match"
    if match_count >= 2:
        return "multi_source_candidate"
    if popularity_score >= 0.85:
        return "high_popularity_backfill"
    return "candidate_recall"


def build_user_topk_scored(
    *,
    candidate_jsonl: Path,
    song_profile_jsonl: Path,
    output_jsonl: Path,
    top_k_items: int = 100,
    artist_decay: float = 0.88,
) -> RankingBuildSummary:
    """构建 user_topk_scored 产物并落盘。"""
    if top_k_items <= 0:
        raise ValueError("top_k_items 必须大于 0")
    if not (0 < artist_decay <= 1):
        raise ValueError("artist_decay 必须在 (0, 1] 范围内")

    candidate_song_ids = _collect_candidate_song_ids(candidate_jsonl)
    song_feature_index = _build_song_feature_index(
        song_profile_jsonl=song_profile_jsonl,
        target_song_ids=candidate_song_ids,
    )

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    total_users = 0
    users_with_candidates = 0
    users_with_ranked_items = 0
    total_ranked_items = 0
    missing_song_feature_count = 0

    with output_jsonl.open("w", encoding="utf-8") as out_file:
        for user_row in _iter_jsonl(candidate_jsonl):
            total_users += 1

            user_key = str(user_row.get("user_key") or "").strip()
            user_key_type = (
                str(user_row.get("user_key_type") or "msno").strip() or "msno"
            )
            preference_genres = {
                str(genre).strip()
                for genre in (user_row.get("preference_genres") or [])
                if str(genre).strip()
            }

            candidates = user_row.get("candidates") or []
            if not isinstance(candidates, list):
                candidates = []

            if candidates:
                users_with_candidates += 1

            max_candidate_score = max(
                (
                    _to_float(item.get("candidate_score"), default=0.0)
                    for item in candidates
                ),
                default=0.0,
            )
            max_match_count = max(
                (_to_int(item.get("match_count"), default=0) for item in candidates),
                default=0,
            )

            base_scored_items: list[dict[str, object]] = []
            for item in candidates:
                song_id = str(item.get("song_id") or "").strip()
                if not song_id:
                    continue

                feature = song_feature_index.get(song_id)
                if feature is None:
                    missing_song_feature_count += 1
                    continue

                candidate_score = _to_float(item.get("candidate_score"), default=0.0)
                match_count = _to_int(item.get("match_count"), default=0)
                recall_norm = (
                    candidate_score / max_candidate_score
                    if max_candidate_score > 0
                    else 0.0
                )
                match_norm = (
                    match_count / max_match_count if max_match_count > 0 else 0.0
                )

                song_genres_raw = feature.get("genre_codes", set())
                if isinstance(song_genres_raw, set):
                    song_genres = {
                        str(code).strip()
                        for code in song_genres_raw
                        if str(code).strip()
                    }
                else:
                    song_genres = set()
                genre_overlap_count = len(song_genres & preference_genres)
                genre_overlap_ratio = (
                    genre_overlap_count / len(preference_genres)
                    if preference_genres
                    else 0.0
                )
                popularity_score = _to_float(feature["popularity_score"], default=0.0)

                # 规则打分定义：
                # - 0.45 召回分：继承候选召回阶段的候选质量。
                # - 0.25 命中分：偏好多流派命中的歌曲优先。
                # - 0.20 重叠分：偏好覆盖比例越高越优。
                # - 0.10 热度分：在冷启动下兼顾稳定性。
                base_score = (
                    0.45 * recall_norm
                    + 0.25 * match_norm
                    + 0.20 * genre_overlap_ratio
                    + 0.10 * popularity_score
                )

                base_scored_items.append(
                    {
                        "song_id": song_id,
                        "artist_name": str(feature["artist_name"] or "").strip(),
                        "candidate_score": round(candidate_score, 6),
                        "match_count": match_count,
                        "popularity_score": round(popularity_score, 6),
                        "genre_overlap_count": genre_overlap_count,
                        "genre_overlap_ratio": round(genre_overlap_ratio, 6),
                        "base_score": round(base_score, 6),
                        "reason": _build_reason(
                            genre_overlap_count=genre_overlap_count,
                            popularity_score=popularity_score,
                            match_count=match_count,
                        ),
                    }
                )

            # 先按基础分排序，再施加艺术家多样性衰减，抑制同歌手刷屏。
            base_scored_items.sort(
                key=lambda x: (-_to_float(x["base_score"]), x["song_id"])
            )
            artist_seen: dict[str, int] = defaultdict(int)
            for scored_item in base_scored_items:
                artist_name = str(scored_item.get("artist_name") or "")
                seen_count = artist_seen[artist_name]
                diversity_factor = artist_decay**seen_count
                scored_item["score"] = round(
                    _to_float(scored_item["base_score"]) * diversity_factor,
                    6,
                )
                artist_seen[artist_name] += 1

            final_items = sorted(
                base_scored_items,
                key=lambda x: (-_to_float(x.get("score"), default=0.0), x["song_id"]),
            )[:top_k_items]

            for idx, ranked_item in enumerate(final_items, start=1):
                ranked_item["rank"] = idx

            if final_items:
                users_with_ranked_items += 1
            total_ranked_items += len(final_items)

            record = {
                "user_key": user_key,
                "user_key_type": user_key_type,
                "strategy": "content_cold_start",
                "ranked_count": len(final_items),
                "items": final_items,
            }
            out_file.write(json.dumps(record, ensure_ascii=False) + "\n")

    average_ranked_items_per_user = (
        total_ranked_items / total_users if total_users else 0.0
    )

    meta_path = output_jsonl.with_suffix(".meta.json")
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "candidate_jsonl": str(candidate_jsonl),
            "song_profile_jsonl": str(song_profile_jsonl),
        },
        "settings": {
            "top_k_items": top_k_items,
            "artist_decay": artist_decay,
        },
        "summary": {
            "total_users": total_users,
            "users_with_candidates": users_with_candidates,
            "users_with_ranked_items": users_with_ranked_items,
            "average_ranked_items_per_user": round(average_ranked_items_per_user, 6),
            "unique_candidate_songs": len(candidate_song_ids),
            "missing_song_feature_count": missing_song_feature_count,
        },
    }
    with meta_path.open("w", encoding="utf-8") as meta_file:
        json.dump(meta, meta_file, ensure_ascii=False, indent=2)

    summary = RankingBuildSummary(
        total_users=total_users,
        users_with_candidates=users_with_candidates,
        users_with_ranked_items=users_with_ranked_items,
        average_ranked_items_per_user=round(average_ranked_items_per_user, 6),
        unique_candidate_songs=len(candidate_song_ids),
        missing_song_feature_count=missing_song_feature_count,
        top_k_items=top_k_items,
        output_path=str(output_jsonl),
        meta_path=str(meta_path),
    )
    return summary


def summary_to_json(summary: RankingBuildSummary) -> str:
    """将构建摘要转换为 JSON 字符串。"""
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2)
