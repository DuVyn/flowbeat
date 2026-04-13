"""Content-Based 特征构建入口。

支持任务：
- song：歌曲内容画像
- user：用户偏好画像
- all：同时执行两类画像

兼容历史别名并自动映射到上述语义任务。
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

try:
    from runtime_paths import detect_workspace_root, resolve_workspace_path
except ModuleNotFoundError as exc:
    if __name__ == "__main__":
        raise RuntimeError(
            "未找到特征构建入口依赖。请在 recsys 目录执行："
            "uv run python features/content_based/build_profiles.py"
        ) from exc
    raise


WORKSPACE_ROOT = detect_workspace_root(anchor_file=Path(__file__).resolve())


def _default_paths() -> tuple[Path, Path, Path]:
    """返回默认路径：项目根目录、processed 目录、特征产物目录。"""
    project_root = WORKSPACE_ROOT
    processed_dir = project_root / "data" / "processed"
    feature_output_dir = (
        project_root / "recsys" / "artifacts" / "content_based" / "features"
    )
    return project_root, processed_dir, feature_output_dir


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    _, processed_dir, feature_output_dir = _default_paths()

    parser = argparse.ArgumentParser(
        description="构建 content_based 的歌曲画像与用户画像。",
    )
    parser.add_argument(
        "--task",
        choices=["song", "user", "all", "p1", "p2"],
        default="all",
        help="选择执行任务：song / user / all（兼容历史别名）。",
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
    parser.add_argument(
        "--allow-external-paths",
        action="store_true",
        help="允许使用工作区外绝对路径。",
    )

    return parser


def main() -> None:
    """执行特征构建任务并输出摘要。"""
    from features.content_based.song_content_profile import (
        build_song_content_profile,
    )
    from features.content_based.user_preference_profile import (
        build_user_preference_profile,
    )

    parser = build_argument_parser()
    args = parser.parse_args()

    allow_external_paths = bool(args.allow_external_paths)

    output_dir = resolve_workspace_path(
        str(args.output_dir),
        workspace_root=WORKSPACE_ROOT,
        allow_external_paths=allow_external_paths,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    result: dict[str, dict[str, object]] = {}
    task = str(args.task).strip().lower()
    if task == "p1":
        task = "song"
    elif task == "p2":
        task = "user"

    if task in {"song", "all"}:
        song_summary = build_song_content_profile(
            songs_csv=resolve_workspace_path(
                str(args.songs_csv),
                workspace_root=WORKSPACE_ROOT,
                allow_external_paths=allow_external_paths,
            ),
            song_genre_m2m_csv=resolve_workspace_path(
                str(args.song_genre_m2m_csv),
                workspace_root=WORKSPACE_ROOT,
                allow_external_paths=allow_external_paths,
            ),
            play_counts_csv=resolve_workspace_path(
                str(args.play_counts_csv),
                workspace_root=WORKSPACE_ROOT,
                allow_external_paths=allow_external_paths,
            ),
            output_jsonl=output_dir / "song_content_profile.jsonl",
        )
        result["song_profile"] = asdict(song_summary)

    if task in {"user", "all"}:
        genre_id_map_csv = (
            resolve_workspace_path(
                str(args.genre_id_map_csv),
                workspace_root=WORKSPACE_ROOT,
                allow_external_paths=allow_external_paths,
            )
            if args.genre_id_map_csv
            else None
        )
        user_summary = build_user_preference_profile(
            users_csv=resolve_workspace_path(
                str(args.users_csv),
                workspace_root=WORKSPACE_ROOT,
                allow_external_paths=allow_external_paths,
            ),
            preference_csv=resolve_workspace_path(
                str(args.user_preference_csv),
                workspace_root=WORKSPACE_ROOT,
                allow_external_paths=allow_external_paths,
            ),
            output_jsonl=output_dir / "user_preference_profile.jsonl",
            strict_preference_file=args.strict_preference_file,
            genre_id_map_csv=genre_id_map_csv,
        )
        result["user_profile"] = asdict(user_summary)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
