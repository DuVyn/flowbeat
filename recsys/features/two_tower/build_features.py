"""Two-Tower 用户侧/物品侧特征构建。"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class TwoTowerFeaturesSummary:
    """特征构建摘要。"""

    user_count: int
    item_count: int
    user_feature_coverage: float
    item_feature_coverage: float
    output_user_features_path: str
    output_item_features_path: str
    output_dictionary_path: str
    output_report_path: str


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [dict(row) for row in reader]


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            yield json.loads(text)


def _to_int(value: str | None, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def _to_float(value: str | None, default: float = 0.0) -> float:
    if value is None or value == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _parse_age(raw_age: str | None) -> int | None:
    if raw_age is None or raw_age == "":
        return None
    try:
        value = int(float(raw_age))
    except ValueError:
        return None
    return value if value > 0 else None


def _to_age_bucket(age: int | None, bins: list[int]) -> str:
    if age is None:
        return "unknown"
    if not bins:
        return str(age)

    sorted_bins = sorted(set(bins))
    if age < sorted_bins[0]:
        return f"lt_{sorted_bins[0]}"

    for low, high in zip(sorted_bins, sorted_bins[1:]):
        if low <= age < high:
            return f"{low}_{high - 1}"

    return f"ge_{sorted_bins[-1]}"


def _to_length_bucket(song_length: int, bins: list[int]) -> str:
    if song_length <= 0:
        return "unknown"
    if not bins:
        return str(song_length)

    sorted_bins = sorted(set(bins))
    if song_length < sorted_bins[0]:
        return f"lt_{sorted_bins[0]}"

    for low, high in zip(sorted_bins, sorted_bins[1:]):
        if low <= song_length < high:
            return f"{low}_{high - 1}"

    return f"ge_{sorted_bins[-1]}"


def _build_index(values: set[str]) -> dict[str, int]:
    return {value: idx for idx, value in enumerate(sorted(values), start=1)}


def build_two_tower_features(
    *,
    users_csv: Path,
    songs_csv: Path,
    play_counts_csv: Path,
    user_preference_csv: Path,
    song_genre_csv: Path,
    interactions_paths: list[Path],
    output_user_features_jsonl: Path,
    output_item_features_jsonl: Path,
    output_dictionary_json: Path,
    output_report_json: Path,
    age_bins: list[int],
    song_length_bins: list[int],
) -> TwoTowerFeaturesSummary:
    """构建用户与物品特征，并输出覆盖率统计。"""
    users = _read_csv_rows(users_csv)
    songs = _read_csv_rows(songs_csv)
    play_counts = _read_csv_rows(play_counts_csv)

    user_preference_map: dict[str, set[str]] = defaultdict(set)
    if user_preference_csv.exists():
        for row in _read_csv_rows(user_preference_csv):
            user_key = str(row.get("msno") or "").strip()
            genre_code = str(row.get("genre_code") or "").strip()
            if user_key and genre_code:
                user_preference_map[user_key].add(genre_code)

    song_genre_map: dict[str, set[str]] = defaultdict(set)
    if song_genre_csv.exists():
        for row in _read_csv_rows(song_genre_csv):
            song_id = str(row.get("song_id") or "").strip()
            genre_code = str(row.get("genre_code") or "").strip()
            if song_id and genre_code:
                song_genre_map[song_id].add(genre_code)

    play_count_map: dict[str, int] = {}
    for row in play_counts:
        song_id = str(row.get("song_id") or "").strip()
        if not song_id:
            continue
        play_count_map[song_id] = _to_int(row.get("total_play_count"), default=0)

    max_play_count = max(play_count_map.values(), default=0)
    popularity_denominator = math.log1p(max_play_count) if max_play_count > 0 else 1.0

    user_activity_counter: Counter[str] = Counter()
    user_positive_counter: Counter[str] = Counter()
    interaction_user_keys: set[str] = set()
    interaction_song_ids: set[str] = set()

    for interaction_path in interactions_paths:
        if not interaction_path.exists():
            continue
        for row in _iter_jsonl(interaction_path):
            user_key = str(row.get("user_key") or "").strip()
            song_id = str(row.get("song_id") or "").strip()
            label = int(row.get("label") or 0)

            if user_key:
                interaction_user_keys.add(user_key)
                user_activity_counter[user_key] += 1
                if label > 0:
                    user_positive_counter[user_key] += 1
            if song_id:
                interaction_song_ids.add(song_id)

    users_by_key: dict[str, dict[str, str]] = {}
    for row in users:
        user_key = str(row.get("msno") or "").strip()
        if user_key:
            users_by_key[user_key] = row

    songs_by_id: dict[str, dict[str, str]] = {}
    for row in songs:
        song_id = str(row.get("song_id") or "").strip()
        if song_id:
            songs_by_id[song_id] = row

    all_user_keys = sorted(set(users_by_key) | interaction_user_keys)
    all_song_ids = sorted(set(songs_by_id) | interaction_song_ids)

    gender_vocab: set[str] = set()
    age_bucket_vocab: set[str] = set()
    genre_vocab: set[str] = set()
    language_vocab: set[str] = set()
    artist_vocab: set[str] = set()
    length_bucket_vocab: set[str] = set()

    output_user_features_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_user_features_jsonl.open("w", encoding="utf-8") as user_file:
        for user_key in all_user_keys:
            row = users_by_key.get(user_key, {})
            gender = str(row.get("gender") or "unknown").strip() or "unknown"
            age = _parse_age(row.get("bd"))
            age_bucket = _to_age_bucket(age, bins=age_bins)
            preferred_genres = sorted(user_preference_map.get(user_key, set()))

            gender_vocab.add(gender)
            age_bucket_vocab.add(age_bucket)
            genre_vocab.update(preferred_genres)

            feature = {
                "user_key": user_key,
                "user_key_type": "msno",
                "gender": gender,
                "age": age,
                "age_bucket": age_bucket,
                "activity_count": int(user_activity_counter.get(user_key, 0)),
                "positive_play_count": int(user_positive_counter.get(user_key, 0)),
                "preferred_genres": preferred_genres,
                "preferred_genre_count": len(preferred_genres),
                "cold_start_ready": len(preferred_genres) > 0,
            }
            user_file.write(json.dumps(feature, ensure_ascii=False) + "\n")

    output_item_features_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_item_features_jsonl.open("w", encoding="utf-8") as item_file:
        for song_id in all_song_ids:
            row = songs_by_id.get(song_id, {})
            song_length = _to_int(row.get("song_length"), default=0)
            song_length_bucket = _to_length_bucket(song_length, bins=song_length_bins)
            language = str(row.get("language") or "unknown").strip() or "unknown"
            artist_name = str(row.get("artist_name") or "unknown_artist").strip()
            if not artist_name:
                artist_name = "unknown_artist"

            total_play_count = play_count_map.get(song_id, 0)
            popularity_score = (
                math.log1p(total_play_count) / popularity_denominator
                if popularity_denominator > 0
                else 0.0
            )
            genres = sorted(song_genre_map.get(song_id, set()))

            language_vocab.add(language)
            artist_vocab.add(artist_name)
            genre_vocab.update(genres)
            length_bucket_vocab.add(song_length_bucket)

            feature = {
                "song_id": song_id,
                "name": str(row.get("name") or "").strip(),
                "artist_name": artist_name,
                "language": language,
                "song_length": song_length,
                "song_length_bucket": song_length_bucket,
                "genres": genres,
                "genre_count": len(genres),
                "total_play_count": total_play_count,
                "popularity_score": round(popularity_score, 6),
            }
            item_file.write(json.dumps(feature, ensure_ascii=False) + "\n")

    feature_dictionaries = {
        "gender_to_idx": _build_index(gender_vocab),
        "age_bucket_to_idx": _build_index(age_bucket_vocab),
        "genre_to_idx": _build_index(genre_vocab),
        "language_to_idx": _build_index(language_vocab),
        "artist_to_idx": _build_index(artist_vocab),
        "song_length_bucket_to_idx": _build_index(length_bucket_vocab),
    }

    output_dictionary_json.parent.mkdir(parents=True, exist_ok=True)
    output_dictionary_json.write_text(
        json.dumps(feature_dictionaries, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    catalog_user_keys = set(users_by_key)
    catalog_song_ids = set(songs_by_id)

    user_feature_coverage = (
        len(interaction_user_keys & catalog_user_keys) / len(interaction_user_keys)
        if interaction_user_keys
        else 1.0
    )
    item_feature_coverage = (
        len(interaction_song_ids & catalog_song_ids) / len(interaction_song_ids)
        if interaction_song_ids
        else 1.0
    )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "users_csv": str(users_csv),
            "songs_csv": str(songs_csv),
            "play_counts_csv": str(play_counts_csv),
            "user_preference_csv": str(user_preference_csv),
            "song_genre_csv": str(song_genre_csv),
            "interactions_paths": [str(path) for path in interactions_paths],
        },
        "settings": {
            "age_bins": age_bins,
            "song_length_bins": song_length_bins,
        },
        "summary": {
            "user_count": len(all_user_keys),
            "item_count": len(all_song_ids),
            "interaction_user_count": len(interaction_user_keys),
            "interaction_song_count": len(interaction_song_ids),
            "user_feature_coverage": round(user_feature_coverage, 6),
            "item_feature_coverage": round(item_feature_coverage, 6),
        },
    }

    output_report_json.parent.mkdir(parents=True, exist_ok=True)
    output_report_json.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return TwoTowerFeaturesSummary(
        user_count=len(all_user_keys),
        item_count=len(all_song_ids),
        user_feature_coverage=round(user_feature_coverage, 6),
        item_feature_coverage=round(item_feature_coverage, 6),
        output_user_features_path=str(output_user_features_jsonl),
        output_item_features_path=str(output_item_features_jsonl),
        output_dictionary_path=str(output_dictionary_json),
        output_report_path=str(output_report_json),
    )
