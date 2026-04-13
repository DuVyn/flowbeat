"""歌曲内容画像构建。

输入：
- songs.csv
- song_genre_m2m.csv
- play_counts.csv

输出：
- song_content_profile.jsonl
- song_content_profile.meta.json
"""

from __future__ import annotations

import csv
import json
import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class SongContentProfileBuildSummary:
    """歌曲内容画像构建摘要。"""

    total_songs: int
    songs_with_genre: int
    songs_with_play_count: int
    max_play_count: int
    output_path: str
    meta_path: str


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    """读取 CSV 行，统一返回字典列表。"""
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [dict(row) for row in reader]


def _to_float(value: str | None) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except ValueError:
        return None


def _to_int(value: str | None, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def _load_song_genres(song_genre_m2m_csv: Path) -> dict[str, set[str]]:
    """加载歌曲到流派编码的映射。"""
    mapping: dict[str, set[str]] = defaultdict(set)
    for row in _read_csv_rows(song_genre_m2m_csv):
        song_id = (row.get("song_id") or "").strip()
        genre_code = (row.get("genre_code") or "").strip()
        if song_id and genre_code:
            mapping[song_id].add(genre_code)
    return mapping


def _load_play_counts(play_counts_csv: Path) -> dict[str, int]:
    """加载歌曲播放次数映射。"""
    mapping: dict[str, int] = {}
    for row in _read_csv_rows(play_counts_csv):
        song_id = (row.get("song_id") or "").strip()
        if not song_id:
            continue
        mapping[song_id] = _to_int(row.get("total_play_count"), default=0)
    return mapping


def build_song_content_profile(
    *,
    songs_csv: Path,
    song_genre_m2m_csv: Path,
    play_counts_csv: Path,
    output_jsonl: Path,
) -> SongContentProfileBuildSummary:
    """构建歌曲内容画像并落盘。"""
    songs = _read_csv_rows(songs_csv)
    song_genres = _load_song_genres(song_genre_m2m_csv)
    play_counts = _load_play_counts(play_counts_csv)

    max_play_count = max(play_counts.values(), default=0)
    popularity_denominator = math.log1p(max_play_count) if max_play_count > 0 else 1.0

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    songs_with_genre = 0
    songs_with_play_count = 0

    with output_jsonl.open("w", encoding="utf-8") as out_file:
        for row in songs:
            song_id = (row.get("song_id") or "").strip()
            if not song_id:
                continue

            genre_codes = sorted(song_genres.get(song_id, set()))
            if genre_codes:
                songs_with_genre += 1

            total_play_count = play_counts.get(song_id, 0)
            if total_play_count > 0:
                songs_with_play_count += 1

            popularity_score = (
                math.log1p(total_play_count) / popularity_denominator
                if popularity_denominator > 0
                else 0.0
            )

            profile = {
                "song_id": song_id,
                "name": (row.get("name") or "").strip(),
                "artist_name": (row.get("artist_name") or "").strip(),
                "language": _to_float(row.get("language")),
                "song_length": _to_int(row.get("song_length"), default=0),
                "audio_object_key": (row.get("audio_object_key") or "").strip(),
                "genre_codes": genre_codes,
                "genre_count": len(genre_codes),
                "total_play_count": total_play_count,
                "popularity_score": round(popularity_score, 6),
            }
            out_file.write(json.dumps(profile, ensure_ascii=False) + "\n")

    meta_path = output_jsonl.with_suffix(".meta.json")
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "songs_csv": str(songs_csv),
            "song_genre_m2m_csv": str(song_genre_m2m_csv),
            "play_counts_csv": str(play_counts_csv),
        },
        "summary": {
            "total_songs": len(songs),
            "songs_with_genre": songs_with_genre,
            "songs_with_play_count": songs_with_play_count,
            "max_play_count": max_play_count,
        },
    }
    with meta_path.open("w", encoding="utf-8") as meta_file:
        json.dump(meta, meta_file, ensure_ascii=False, indent=2)

    summary = SongContentProfileBuildSummary(
        total_songs=len(songs),
        songs_with_genre=songs_with_genre,
        songs_with_play_count=songs_with_play_count,
        max_play_count=max_play_count,
        output_path=str(output_jsonl),
        meta_path=str(meta_path),
    )
    return summary


def summary_to_json(summary: SongContentProfileBuildSummary) -> str:
    """将构建摘要序列化为 JSON 字符串。"""
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2)
