"""用户偏好画像构建。

输入：
- users.csv
- user_genre_preference_m2m.csv（建议列：msno/user_id + genre_code）

输出：
- user_preference_profile.jsonl
- user_preference_profile.meta.json
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(slots=True)
class UserPreferenceProfileBuildSummary:
    """用户偏好画像构建摘要。"""

    total_users: int
    users_with_preferences: int
    average_preference_count: float
    missing_preference_file: bool
    output_path: str
    meta_path: str


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [dict(row) for row in reader]


def _detect_user_key_field(user_row: dict[str, str]) -> str:
    """根据用户表字段自动选择主键。

    优先 `id`，否则退化为 `msno`。
    """
    if "id" in user_row:
        return "id"
    if "msno" in user_row:
        return "msno"
    raise ValueError("users.csv 缺少 id/msno 字段，无法构建用户画像。")


def _load_genre_id_map(genre_id_map_csv: Path | None) -> dict[str, str]:
    """加载 genre_id -> genre_code 映射（可选）。"""
    if genre_id_map_csv is None:
        return {}

    mapping: dict[str, str] = {}
    for row in _read_csv_rows(genre_id_map_csv):
        genre_id = (row.get("id") or "").strip()
        genre_code = (row.get("genre_code") or "").strip()
        if genre_id and genre_code:
            mapping[genre_id] = genre_code
    return mapping


def _load_preference_mapping(
    *,
    preference_rows: list[dict[str, str]],
    user_key_field: str,
    genre_id_map: dict[str, str],
) -> dict[str, set[str]]:
    """加载用户偏好流派映射。"""
    mapping: dict[str, set[str]] = defaultdict(set)

    for row in preference_rows:
        if user_key_field == "id":
            user_key = (row.get("user_id") or row.get("id") or "").strip()
        else:
            user_key = (row.get("msno") or "").strip()

        if not user_key:
            continue

        genre_code = (row.get("genre_code") or "").strip()
        if not genre_code:
            genre_id = (row.get("genre_id") or "").strip()
            if genre_id:
                mapped_code = genre_id_map.get(genre_id)
                if mapped_code:
                    genre_code = mapped_code

        if genre_code:
            mapping[user_key].add(genre_code)

    return mapping


def _parse_age(raw_age: str | None) -> int | None:
    if raw_age is None or raw_age == "":
        return None
    try:
        age = int(float(raw_age))
    except ValueError:
        return None
    return age if age > 0 else None


def build_user_preference_profile(
    *,
    users_csv: Path,
    preference_csv: Path,
    output_jsonl: Path,
    strict_preference_file: bool = False,
    genre_id_map_csv: Path | None = None,
) -> UserPreferenceProfileBuildSummary:
    """构建用户偏好画像并落盘。"""
    users = _read_csv_rows(users_csv)
    if not users:
        raise ValueError("users.csv 为空，无法构建用户偏好画像。")

    user_key_field = _detect_user_key_field(users[0])
    genre_id_map = _load_genre_id_map(genre_id_map_csv)

    missing_preference_file = False
    if preference_csv.exists():
        preference_rows = _read_csv_rows(preference_csv)
    else:
        if strict_preference_file:
            raise FileNotFoundError(
                f"未找到偏好输入文件：{preference_csv}。"
                "请先准备 user_genre_preference_m2m.csv。"
            )
        preference_rows = []
        missing_preference_file = True

    preference_mapping = _load_preference_mapping(
        preference_rows=preference_rows,
        user_key_field=user_key_field,
        genre_id_map=genre_id_map,
    )

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    users_with_preferences = 0
    total_preferences = 0

    with output_jsonl.open("w", encoding="utf-8") as out_file:
        for row in users:
            user_key = (row.get(user_key_field) or "").strip()
            if not user_key:
                continue

            genres = sorted(preference_mapping.get(user_key, set()))
            if genres:
                users_with_preferences += 1
            total_preferences += len(genres)

            profile = {
                "user_key": user_key,
                "user_key_type": user_key_field,
                "gender": (row.get("gender") or "unknown").strip() or "unknown",
                "age": _parse_age(row.get("bd")),
                "preference_genres": genres,
                "preference_genre_count": len(genres),
                "cold_start_ready": len(genres) > 0,
            }
            out_file.write(json.dumps(profile, ensure_ascii=False) + "\n")

    avg_count = total_preferences / len(users) if users else 0.0

    meta_path = output_jsonl.with_suffix(".meta.json")
    meta = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input": {
            "users_csv": str(users_csv),
            "preference_csv": str(preference_csv),
            "genre_id_map_csv": str(genre_id_map_csv) if genre_id_map_csv else None,
        },
        "summary": {
            "total_users": len(users),
            "users_with_preferences": users_with_preferences,
            "average_preference_count": round(avg_count, 6),
            "missing_preference_file": missing_preference_file,
        },
    }
    with meta_path.open("w", encoding="utf-8") as meta_file:
        json.dump(meta, meta_file, ensure_ascii=False, indent=2)

    summary = UserPreferenceProfileBuildSummary(
        total_users=len(users),
        users_with_preferences=users_with_preferences,
        average_preference_count=round(avg_count, 6),
        missing_preference_file=missing_preference_file,
        output_path=str(output_jsonl),
        meta_path=str(meta_path),
    )
    return summary


def summary_to_json(summary: UserPreferenceProfileBuildSummary) -> str:
    """将构建摘要序列化为 JSON 字符串。"""
    return json.dumps(asdict(summary), ensure_ascii=False, indent=2)
