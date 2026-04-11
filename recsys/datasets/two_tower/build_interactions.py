"""P1：Two-Tower 训练样本构建。"""

from __future__ import annotations

import csv
import json
import random
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class TwoTowerInteractionsSummary:
    """样本构建摘要。"""

    total_positive_events: int
    total_negative_events: int
    train_rows: int
    valid_rows: int
    test_rows: int
    removed_low_activity_events: int
    invalid_rows: int
    output_train_path: str
    output_valid_path: str
    output_test_path: str
    output_meta_path: str


def _to_int(value: str | None, default: int = 0) -> int:
    if value is None or value == "":
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def _parse_timestamp(raw: str | None) -> datetime | None:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None

    candidates = (text, text.replace(" ", "T"))
    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue
    return None


def _read_song_catalog(songs_csv: Path) -> set[str]:
    song_ids: set[str] = set()
    with songs_csv.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            song_id = str(row.get("song_id") or "").strip()
            if song_id:
                song_ids.add(song_id)
    return song_ids


def _read_user_catalog(users_csv: Path) -> set[str]:
    user_keys: set[str] = set()
    with users_csv.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            user_key = str(row.get("msno") or "").strip()
            if user_key:
                user_keys.add(user_key)
    return user_keys


def _sample_negative_song_ids(
    *,
    rng: random.Random,
    all_song_ids: list[str],
    blocked_song_ids: set[str],
    sample_size: int,
) -> list[str]:
    """按用户已交互歌曲排除后进行可复现负采样。"""
    if sample_size <= 0 or not all_song_ids:
        return []

    if len(blocked_song_ids) >= len(all_song_ids):
        return []

    selected: list[str] = []
    selected_set: set[str] = set()
    attempts = 0
    max_attempts = max(sample_size * 20, 200)

    while len(selected) < sample_size and attempts < max_attempts:
        attempts += 1
        candidate = all_song_ids[rng.randrange(0, len(all_song_ids))]
        if candidate in blocked_song_ids or candidate in selected_set:
            continue
        selected.append(candidate)
        selected_set.add(candidate)

    if len(selected) >= sample_size:
        return selected

    for candidate in all_song_ids:
        if candidate in blocked_song_ids or candidate in selected_set:
            continue
        selected.append(candidate)
        selected_set.add(candidate)
        if len(selected) >= sample_size:
            break

    return selected


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_two_tower_interactions(
    *,
    users_csv: Path,
    songs_csv: Path,
    play_histories_csv: Path,
    output_train_jsonl: Path,
    output_valid_jsonl: Path,
    output_test_jsonl: Path,
    output_meta_json: Path,
    positive_target_threshold: int = 1,
    negative_sampling_ratio: int = 2,
    train_ratio: float = 0.8,
    valid_ratio: float = 0.1,
    test_ratio: float = 0.1,
    min_user_positive_events: int = 1,
    seed: int = 20260410,
    sample_limit: int | None = 200_000,
) -> TwoTowerInteractionsSummary:
    """构建 train/valid/test 三份交互样本。"""
    if positive_target_threshold < 1:
        raise ValueError("positive_target_threshold 必须 >= 1")
    if negative_sampling_ratio < 0:
        raise ValueError("negative_sampling_ratio 不能为负数")
    if min_user_positive_events < 1:
        raise ValueError("min_user_positive_events 必须 >= 1")

    ratio_sum = train_ratio + valid_ratio + test_ratio
    if abs(ratio_sum - 1.0) > 1e-6:
        raise ValueError("train/valid/test 切分比例之和必须为 1")

    song_catalog = _read_song_catalog(songs_csv)
    user_catalog = _read_user_catalog(users_csv)

    positive_events: list[dict[str, object]] = []
    invalid_rows = 0

    with play_histories_csv.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if sample_limit is not None and len(positive_events) >= sample_limit:
                break

            user_key = str(row.get("msno") or "").strip()
            song_id = str(row.get("song_id") or "").strip()
            if not user_key or not song_id:
                invalid_rows += 1
                continue

            if user_key not in user_catalog or song_id not in song_catalog:
                invalid_rows += 1
                continue

            target = _to_int(row.get("target"), default=0)
            if target < positive_target_threshold:
                continue

            event_time = _parse_timestamp(row.get("played_at")) or _parse_timestamp(
                row.get("created_at")
            )
            if event_time is None:
                invalid_rows += 1
                continue

            positive_events.append(
                {
                    "user_key": user_key,
                    "song_id": song_id,
                    "target": target,
                    "event_time": event_time,
                }
            )

    if not positive_events:
        raise ValueError("未找到可用正样本，无法继续 P1。")

    user_positive_counter: Counter[str] = Counter(
        str(event["user_key"]) for event in positive_events
    )
    positive_events = [
        event
        for event in positive_events
        if user_positive_counter[str(event["user_key"])] >= min_user_positive_events
    ]

    removed_low_activity_events = sum(
        count
        for _user, count in user_positive_counter.items()
        if count < min_user_positive_events
    )

    if not positive_events:
        raise ValueError("按 min_user_positive_events 过滤后无可用正样本。")

    positive_events.sort(
        key=lambda event: datetime.fromisoformat(str(event["event_time"]))
    )

    total_positive = len(positive_events)
    train_end = int(total_positive * train_ratio)
    valid_end = int(total_positive * (train_ratio + valid_ratio))

    split_positive_events = {
        "train": positive_events[:train_end],
        "valid": positive_events[train_end:valid_end],
        "test": positive_events[valid_end:],
    }

    user_seen_song_ids: dict[str, set[str]] = defaultdict(set)
    for event in positive_events:
        user_seen_song_ids[str(event["user_key"])].add(str(event["song_id"]))

    rng = random.Random(seed)
    all_song_ids = sorted(song_catalog)

    split_rows: dict[str, list[dict[str, object]]] = {
        "train": [],
        "valid": [],
        "test": [],
    }

    total_negative_events = 0

    for split_name, events in split_positive_events.items():
        rows = split_rows[split_name]
        for event in events:
            user_key = str(event["user_key"])
            song_id = str(event["song_id"])
            target_obj = event["target"]
            target_value = (
                target_obj if isinstance(target_obj, int) else _to_int(str(target_obj))
            )
            event_time = datetime.fromisoformat(str(event["event_time"]))
            event_time_iso = event_time.isoformat()

            rows.append(
                {
                    "split": split_name,
                    "user_key": user_key,
                    "user_key_type": "msno",
                    "song_id": song_id,
                    "label": 1,
                    "target": target_value,
                    "event_time": event_time_iso,
                    "sample_source": "observed_play",
                }
            )

            negative_song_ids = _sample_negative_song_ids(
                rng=rng,
                all_song_ids=all_song_ids,
                blocked_song_ids=user_seen_song_ids[user_key],
                sample_size=negative_sampling_ratio,
            )
            for negative_song_id in negative_song_ids:
                rows.append(
                    {
                        "split": split_name,
                        "user_key": user_key,
                        "user_key_type": "msno",
                        "song_id": negative_song_id,
                        "label": 0,
                        "target": 0,
                        "event_time": event_time_iso,
                        "sample_source": "negative_sampling",
                    }
                )
            total_negative_events += len(negative_song_ids)

    _write_jsonl(output_train_jsonl, split_rows["train"])
    _write_jsonl(output_valid_jsonl, split_rows["valid"])
    _write_jsonl(output_test_jsonl, split_rows["test"])

    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "users_csv": str(users_csv),
            "songs_csv": str(songs_csv),
            "play_histories_csv": str(play_histories_csv),
        },
        "settings": {
            "positive_target_threshold": positive_target_threshold,
            "negative_sampling_ratio": negative_sampling_ratio,
            "train_ratio": train_ratio,
            "valid_ratio": valid_ratio,
            "test_ratio": test_ratio,
            "min_user_positive_events": min_user_positive_events,
            "seed": seed,
            "sample_limit": sample_limit,
        },
        "summary": {
            "total_positive_events": total_positive,
            "total_negative_events": total_negative_events,
            "train_rows": len(split_rows["train"]),
            "valid_rows": len(split_rows["valid"]),
            "test_rows": len(split_rows["test"]),
            "removed_low_activity_events": removed_low_activity_events,
            "invalid_rows": invalid_rows,
        },
    }

    output_meta_json.parent.mkdir(parents=True, exist_ok=True)
    output_meta_json.write_text(
        json.dumps(meta, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return TwoTowerInteractionsSummary(
        total_positive_events=total_positive,
        total_negative_events=total_negative_events,
        train_rows=len(split_rows["train"]),
        valid_rows=len(split_rows["valid"]),
        test_rows=len(split_rows["test"]),
        removed_low_activity_events=removed_low_activity_events,
        invalid_rows=invalid_rows,
        output_train_path=str(output_train_jsonl),
        output_valid_path=str(output_valid_jsonl),
        output_test_path=str(output_test_jsonl),
        output_meta_path=str(output_meta_json),
    )
