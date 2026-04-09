"""Content-Based P3 候选召回构建入口。"""

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


def _default_paths() -> tuple[Path, Path]:
    """返回默认输入输出目录。"""
    project_root = Path(__file__).resolve().parents[3]
    artifacts_root = project_root / "recsys" / "artifacts" / "content_based"
    return artifacts_root / "features", artifacts_root / "candidates"


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    feature_dir, candidate_dir = _default_paths()

    parser = argparse.ArgumentParser(
        description="构建 content_based 的 P3 用户候选集。"
    )
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
    return parser


def main() -> None:
    """执行候选召回构建。"""
    from inference.content_based.candidate_recall import build_user_candidate_set

    parser = build_argument_parser()
    args = parser.parse_args()

    summary = build_user_candidate_set(
        user_profile_jsonl=Path(args.user_profile_jsonl),
        song_profile_jsonl=Path(args.song_profile_jsonl),
        output_jsonl=Path(args.output_jsonl),
        top_k_candidates=args.top_k_candidates,
        max_songs_per_genre=args.max_songs_per_genre,
    )

    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
