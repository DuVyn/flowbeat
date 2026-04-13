"""Content-Based 排序打分构建入口。"""

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
            "未找到排序打分入口依赖。请在 recsys 目录执行："
            "uv run python inference/content_based/build_ranked.py"
        ) from exc
    raise


WORKSPACE_ROOT = detect_workspace_root(anchor_file=Path(__file__).resolve())


def _default_paths() -> tuple[Path, Path, Path]:
    """返回默认输入输出目录。"""
    project_root = WORKSPACE_ROOT
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
        description="构建 content_based 用户 TopK 打分结果。"
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
    parser.add_argument(
        "--allow-external-paths",
        action="store_true",
        help="允许使用工作区外绝对路径。",
    )
    return parser


def main() -> None:
    """执行规则打分构建。"""
    from inference.content_based.rank_scoring import build_user_topk_scored

    parser = build_argument_parser()
    args = parser.parse_args()

    allow_external_paths = bool(args.allow_external_paths)

    summary = build_user_topk_scored(
        candidate_jsonl=resolve_workspace_path(
            str(args.candidate_jsonl),
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
        top_k_items=args.top_k_items,
        artist_decay=args.artist_decay,
    )

    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
