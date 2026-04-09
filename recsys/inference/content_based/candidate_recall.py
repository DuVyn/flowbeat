"""P3：Content-Based 候选召回。

输入：
- song_content_profile.jsonl（P1 产物）
- user_preference_profile.jsonl（P2 产物）

输出：
- user_candidate_set.jsonl
- user_candidate_set.meta.json
"""

from __future__ import annotations

import heapq
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class CandidateRecallBuildSummary:
    """候选召回构建摘要。"""

    total_users: int
    users_with_preferences: int
    users_with_candidates: int
    average_candidates_per_user: float
    indexed_genres: int
    top_k_candidates: int
    max_songs_per_genre: int
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
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _to_int(value: object, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _build_genre_top_song_index(
    *,
    song_profile_jsonl: Path,
    max_songs_per_genre: int,
) -> dict[str, list[tuple[str, float, int]]]:
    """基于歌曲画像构建流派到歌曲 TopN 索引。"""
    genre_heaps: dict[str, list[tuple[float, int, str]]] = defaultdict(list)

    for row in _iter_jsonl(song_profile_jsonl):
        song_id = str(row.get("song_id") or "").strip()
        if not song_id:
            continue

        genre_codes = row.get("genre_codes") or []
        if not isinstance(genre_codes, list):
            continue

        popularity_score = _to_float(row.get("popularity_score"), default=0.0)
        total_play_count = _to_int(row.get("total_play_count"), default=0)
        sort_key = (popularity_score, total_play_count, song_id)

        for genre in genre_codes:
            genre_code = str(genre).strip()
            if not genre_code:
                continue

            heap = genre_heaps[genre_code]
            if len(heap) < max_songs_per_genre:
                heapq.heappush(heap, sort_key)
            elif sort_key > heap[0]:
                heapq.heapreplace(heap, sort_key)

    genre_index: dict[str, list[tuple[str, float, int]]] = {}
    for genre_code, heap in genre_heaps.items():
        # 按流派内热度从高到低排序。
        sorted_items = sorted(heap, reverse=True)
        genre_index[genre_code] = [
            (song_id, popularity_score, total_play_count)
            for popularity_score, total_play_count, song_id in sorted_items
        ]

    return genre_index


def build_user_candidate_set(
    *,
    user_profile_jsonl: Path,
    song_profile_jsonl: Path,
    output_jsonl: Path,
    top_k_candidates: int = 120,
    max_songs_per_genre: int = 400,
) -> CandidateRecallBuildSummary:
    """构建 user_candidate_set 并落盘。"""
    genre_index = _build_genre_top_song_index(
        song_profile_jsonl=song_profile_jsonl,
        max_songs_per_genre=max_songs_per_genre,
    )

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    total_users = 0
    users_with_preferences = 0
    users_with_candidates = 0
    total_candidate_count = 0

    with output_jsonl.open("w", encoding="utf-8") as out_file:
        for user in _iter_jsonl(user_profile_jsonl):
            total_users += 1

            user_key = str(user.get("user_key") or "").strip()
            user_key_type = str(user.get("user_key_type") or "msno").strip() or "msno"
            preference_genres = [
                str(genre).strip()
                for genre in (user.get("preference_genres") or [])
                if str(genre).strip()
            ]

            if preference_genres:
                users_with_preferences += 1

            # 召回打分说明：
            # - 同时命中多个偏好流派的歌曲优先。
            # - 流派内排名越靠前、歌曲流行度越高，候选分越高。
            candidate_stats: dict[str, list[float]] = {}
            for genre_code in preference_genres:
                songs = genre_index.get(genre_code, [])
                for rank, (song_id, popularity_score, _play_count) in enumerate(
                    songs, start=1
                ):
                    rank_weight = (
                        (max_songs_per_genre - rank + 1) / max_songs_per_genre
                        if rank <= max_songs_per_genre
                        else 0.0
                    )
                    score = 0.7 * rank_weight + 0.3 * popularity_score

                    if song_id not in candidate_stats:
                        candidate_stats[song_id] = [0.0, 0.0]
                    candidate_stats[song_id][0] += 1.0
                    candidate_stats[song_id][1] += score

            ranked_candidates = sorted(
                candidate_stats.items(),
                key=lambda item: (-item[1][0], -item[1][1], item[0]),
            )

            top_candidates = ranked_candidates[:top_k_candidates]
            candidates = [
                {
                    "song_id": song_id,
                    "match_count": int(stats[0]),
                    "candidate_score": round(stats[1], 6),
                }
                for song_id, stats in top_candidates
            ]

            candidate_count = len(candidates)
            total_candidate_count += candidate_count
            if candidate_count > 0:
                users_with_candidates += 1

            record = {
                "user_key": user_key,
                "user_key_type": user_key_type,
                "preference_genres": preference_genres,
                "candidate_count": candidate_count,
                "candidates": candidates,
            }
            out_file.write(json.dumps(record, ensure_ascii=False) + "\n")

    average_candidates_per_user = (
        total_candidate_count / total_users if total_users else 0.0
    )

    meta_path = output_jsonl.with_suffix(".meta.json")
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "user_profile_jsonl": str(user_profile_jsonl),
            "song_profile_jsonl": str(song_profile_jsonl),
        },
        "settings": {
            "top_k_candidates": top_k_candidates,
            "max_songs_per_genre": max_songs_per_genre,
        },
        "summary": {
            "total_users": total_users,
            "users_with_preferences": users_with_preferences,
            "users_with_candidates": users_with_candidates,
            "average_candidates_per_user": round(average_candidates_per_user, 6),
            "indexed_genres": len(genre_index),
        },
    }
    with meta_path.open("w", encoding="utf-8") as meta_file:
        json.dump(meta, meta_file, ensure_ascii=False, indent=2)

    summary = CandidateRecallBuildSummary(
        total_users=total_users,
        users_with_preferences=users_with_preferences,
        users_with_candidates=users_with_candidates,
        average_candidates_per_user=round(average_candidates_per_user, 6),
        indexed_genres=len(genre_index),
        top_k_candidates=top_k_candidates,
        max_songs_per_genre=max_songs_per_genre,
        output_path=str(output_jsonl),
        meta_path=str(meta_path),
    )
    return summary


def summary_to_json(summary: CandidateRecallBuildSummary) -> str:
    """将构建摘要转换为 JSON 字符串。"""
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2)
