"""Content-Based P4 排序打分构建入口。"""

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
    """返回默认输入输出目录。"""
    project_root = Path(__file__).resolve().parents[3]
    artifacts_root = project_root / "recsys" / "artifacts" / "content_based"
    return (
        artifacts_root / "candidates",
        artifacts_root / "features",
        artifacts_root / "ranked",
    )


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    candidate_dir, feature_dir, ranked_dir = _default_paths()

    parser = argparse.ArgumentParser(
        description="构建 content_based 的 P4 用户 TopK 打分结果。"
    )
    parser.add_argument(
        "--candidate-jsonl",
        default=str(candidate_dir / "user_candidate_set.jsonl"),
    )
    parser.add_argument(
        "--song-profile-jsonl",
        default=str(feature_dir / "song_content_profile.jsonl"),
    )
    parser.add_argument(
        "--output-jsonl",
        default=str(ranked_dir / "user_topk_scored.jsonl"),
    )
    parser.add_argument(
        "--top-k-items",
        type=int,
        default=100,
        help="每个用户输出的最终 TopK 数量。",
    )
    parser.add_argument(
        "--artist-decay",
        type=float,
        default=0.88,
        help="艺术家重复惩罚系数，越小惩罚越强，范围 (0, 1]。",
    )
    return parser


def main() -> None:
    """执行 P4 规则打分构建。"""
    from inference.content_based.rank_scoring import build_user_topk_scored

    parser = build_argument_parser()
    args = parser.parse_args()

    summary = build_user_topk_scored(
        candidate_jsonl=Path(args.candidate_jsonl),
        song_profile_jsonl=Path(args.song_profile_jsonl),
        output_jsonl=Path(args.output_jsonl),
        top_k_items=args.top_k_items,
        artist_decay=args.artist_decay,
    )

    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
