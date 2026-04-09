"""Content-Based P1/P2 特征产物构建入口。

支持任务：
- p1：歌曲内容画像
- p2：用户偏好画像
- all：同时执行 p1 + p2
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

CURRENT_FILE = Path(__file__).resolve()
RECSYS_ROOT = CURRENT_FILE.parents[2]
WORKSPACE_ROOT = CURRENT_FILE.parents[3]

for path_candidate in (WORKSPACE_ROOT, RECSYS_ROOT):
    path_str = str(path_candidate)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)


def _default_paths() -> tuple[Path, Path, Path]:
    """返回默认路径：项目根目录、processed 目录、特征产物目录。"""
    project_root = Path(__file__).resolve().parents[3]
    processed_dir = project_root / "data" / "processed"
    feature_output_dir = (
        project_root / "recsys" / "artifacts" / "content_based" / "features"
    )
    return project_root, processed_dir, feature_output_dir


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    _, processed_dir, feature_output_dir = _default_paths()

    parser = argparse.ArgumentParser(
        description="构建 content_based 的 P1/P2 特征产物。",
    )
    parser.add_argument(
        "--task",
        choices=["p1", "p2", "all"],
        default="all",
        help="选择执行任务：p1 / p2 / all。",
    )

    parser.add_argument("--songs-csv", default=str(processed_dir / "songs.csv"))
    parser.add_argument(
        "--song-genre-m2m-csv",
        default=str(processed_dir / "song_genre_m2m.csv"),
    )
    parser.add_argument(
        "--play-counts-csv",
        default=str(processed_dir / "play_counts.csv"),
    )

    parser.add_argument("--users-csv", default=str(processed_dir / "users.csv"))
    parser.add_argument(
        "--user-preference-csv",
        default=str(processed_dir / "user_genre_preference_m2m.csv"),
    )
    parser.add_argument(
        "--genre-id-map-csv",
        default="",
        help="可选：当偏好文件只有 genre_id 时，提供 id->genre_code 映射文件。",
    )
    parser.add_argument(
        "--strict-preference-file",
        action="store_true",
        help="开启后，若 user_preference 输入文件缺失将直接报错退出。",
    )

    parser.add_argument(
        "--output-dir",
        default=str(feature_output_dir),
        help="产物输出目录。",
    )

    return parser


def main() -> None:
    """执行 P1/P2 任务并输出摘要。"""
    from features.content_based.song_content_profile import build_song_content_profile
    from features.content_based.user_preference_profile import (
        build_user_preference_profile,
    )

    parser = build_argument_parser()
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, dict[str, object]] = {}

    if args.task in {"p1", "all"}:
        p1_summary = build_song_content_profile(
            songs_csv=Path(args.songs_csv),
            song_genre_m2m_csv=Path(args.song_genre_m2m_csv),
            play_counts_csv=Path(args.play_counts_csv),
            output_jsonl=output_dir / "song_content_profile.jsonl",
        )
        result["p1"] = asdict(p1_summary)

    if args.task in {"p2", "all"}:
        genre_id_map_csv = (
            Path(args.genre_id_map_csv) if args.genre_id_map_csv else None
        )
        p2_summary = build_user_preference_profile(
            users_csv=Path(args.users_csv),
            preference_csv=Path(args.user_preference_csv),
            output_jsonl=output_dir / "user_preference_profile.jsonl",
            strict_preference_file=args.strict_preference_file,
            genre_id_map_csv=genre_id_map_csv,
        )
        result["p2"] = asdict(p2_summary)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
