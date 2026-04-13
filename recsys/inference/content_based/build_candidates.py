"""基于内容的候选召回构建入口。"""

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
            "未找到候选召回入口依赖。请在 recsys 目录执行："
            "uv run python inference/content_based/build_candidates.py"
        ) from exc
    raise


WORKSPACE_ROOT = detect_workspace_root(anchor_file=Path(__file__).resolve())


def _default_paths() -> tuple[Path, Path]:
    """返回默认输入输出目录。"""
    project_root = WORKSPACE_ROOT
    artifacts_root = project_root / "recsys" / "artifacts" / "content_based"
    return artifacts_root / "features", artifacts_root / "candidates"


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    feature_dir, candidate_dir = _default_paths()

    parser = argparse.ArgumentParser(description="构建 content_based 用户候选集。")
    parser.add_argument(
        "--user-profile-jsonl",
        default=str(feature_dir / "user_preference_profile.jsonl"),
    )
    parser.add_argument(
        "--song-profile-jsonl",
        default=str(feature_dir / "song_content_profile.jsonl"),
    )
    parser.add_argument(
        "--output-jsonl",
        default=str(candidate_dir / "user_candidate_set.jsonl"),
    )
    parser.add_argument(
        "--top-k-candidates",
        type=int,
        default=120,
        help="每个用户保留的候选数量。",
    )
    parser.add_argument(
        "--max-songs-per-genre",
        type=int,
        default=400,
        help="每个流派参与召回的歌曲上限。",
    )
    parser.add_argument(
        "--allow-external-paths",
        action="store_true",
        help="允许使用工作区外绝对路径。",
    )
    return parser


def main() -> None:
    """执行候选召回构建。"""
    from inference.content_based.candidate_recall import build_user_candidate_set

    parser = build_argument_parser()
    args = parser.parse_args()

    allow_external_paths = bool(args.allow_external_paths)

    summary = build_user_candidate_set(
        user_profile_jsonl=resolve_workspace_path(
            str(args.user_profile_jsonl),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        ),
        song_profile_jsonl=resolve_workspace_path(
            str(args.song_profile_jsonl),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        ),
        output_jsonl=resolve_workspace_path(
            str(args.output_jsonl),
            workspace_root=WORKSPACE_ROOT,
            allow_external_paths=allow_external_paths,
        ),
        top_k_candidates=args.top_k_candidates,
        max_songs_per_genre=args.max_songs_per_genre,
    )

    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
