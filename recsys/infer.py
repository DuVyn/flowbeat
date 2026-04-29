"""双塔模型推理入口 - 简化版（专注于生成 JSONL 推荐结果）。

用法:
    # 默认从预设路径读取 embeddings 并生成推荐结果
    uv run python infer.py
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from inference.two_tower.rank_scoring import build_two_tower_topk_from_embeddings


def _create_empty_interactions_jsonl(path: Path) -> None:
    """创建空的 interactions JSONL 文件（表示无已看样本）。

    build_two_tower_topk_from_embeddings 需要此文件来过滤已见样本。
    空文件表示所有物品都可推荐。
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")


def build_argument_parser() -> argparse.ArgumentParser:
    """构建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        description="Two-Tower 推理：从 embeddings 生成用户 TopK 推荐结果（JSONL 格式）",
    )
    parser.add_argument(
        "--embeddings-dir",
        default="recsys/artifacts/two_tower/server_local/embeddings",
        help="Embeddings 目录路径（包含 user_embeddings.pt, item_embeddings.pt 等）",
    )
    parser.add_argument(
        "--output-jsonl",
        default="recsys/artifacts/two_tower/server_local/ranked/user_topk_scored.jsonl",
        help="输出 JSONL 推荐结果文件路径",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=100,
        help="每用户返回的推荐数量，默认 100",
    )
    parser.add_argument(
        "--score-batch-size",
        type=int,
        default=64,
        help="用户批次大小（显存不足时可调小），默认 64",
    )
    parser.add_argument(
        "--item-block-size",
        type=int,
        default=20000,
        help="物品向量分块大小，避免显存溢出，默认 20000",
    )
    parser.add_argument(
        "--device",
        default="auto",
        help="推理设备: auto/cuda/mps/cpu，默认 auto",
    )
    return parser


def main() -> None:
    """执行推理任务。"""
    parser = build_argument_parser()
    args = parser.parse_args()

    embeddings_dir = Path(args.embeddings_dir).resolve()
    output_jsonl = Path(args.output_jsonl).resolve()

    # 确保输出文件的父目录存在
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    # 验证 embeddings 文件存在
    user_emb = embeddings_dir / "user_embeddings.pt"
    item_emb = embeddings_dir / "item_embeddings.pt"
    user_idx = embeddings_dir / "user_index.json"
    item_idx = embeddings_dir / "item_index.json"

    files_to_check = [
        (user_emb, "user_embeddings.pt"),
        (item_emb, "item_embeddings.pt"),
        (user_idx, "user_index.json"),
        (item_idx, "item_index.json"),
    ]

    for path, name in files_to_check:
        if not path.exists():
            raise FileNotFoundError(
                f"缺少 embeddings 文件: {name}\n"
                f"期望位置: {path}\n"
                f"请先运行 export_embeddings.py 导出模型向量。"
            )

    print(f"[推理] Embeddings 目录: {embeddings_dir}", flush=True)
    print(f"[推理] 输出文件: {output_jsonl}", flush=True)
    print(f"[推理] 推荐数量: top-{args.top_k}", flush=True)
    print(f"[推理] 推理设备: {args.device}", flush=True)

    # 创建临时 interactions JSONL（空文件 = 无已看样本、对所有物品推荐）
    temp_interactions = output_jsonl.parent / ".tmp_interactions_train.jsonl"
    _create_empty_interactions_jsonl(temp_interactions)

    try:
        print("\n[推理] 生成 TopK 推荐...", flush=True)
        summary = build_two_tower_topk_from_embeddings(
            user_embedding_path=user_emb,
            item_embedding_path=item_emb,
            user_index_json=user_idx,
            item_index_json=item_idx,
            interactions_train_jsonl=temp_interactions,
            output_jsonl=output_jsonl,
            top_k_items=int(args.top_k),
            score_batch_size=int(args.score_batch_size),
            item_block_size=int(args.item_block_size),
            device=str(args.device),
        )

        print("\n[推理] 推荐结果生成完成！", flush=True)

        # 输出统计信息
        print("\n=== 推理统计 ===", flush=True)
        summary_dict = asdict(summary)
        for key, value in summary_dict.items():
            if isinstance(value, float):
                print(f"  {key}: {value:.6f}")
            elif isinstance(value, str) and len(value) > 80:
                print(f"  {key}: {value[:60]}...")
            else:
                print(f"  {key}: {value}")

        # 生成元数据文件（用于跟踪）
        meta = {
            "output_jsonl": str(output_jsonl),
            "top_k": int(args.top_k),
            "summary": summary_dict,
        }
        meta_path = output_jsonl.with_suffix(".meta.json")
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)
        print(f"\n[推理] 元数据文件: {meta_path}", flush=True)

    finally:
        # 清理临时文件
        if temp_interactions.exists():
            temp_interactions.unlink()


if __name__ == "__main__":
    main()
