"""从已有 checkpoint 导出 user/item embedding 与索引映射。

用法示例：
  cd recsys
  uv run python export_embeddings.py --config configs/two_tower/config_local.yaml --checkpoint best

支持的 checkpoint 参数：`best`、`last` 或者任意可访问的路径/URI。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml

from training.two_tower.config_schema import TrainingConfig, parse_config
from training.two_tower.data_engine import load_datasets
from training.two_tower.model_builder import build_model, resolve_device
from training.two_tower.storage_backend import create_backend


def _detect_workspace_root() -> Path:
    this = Path(__file__).resolve()
    for candidate in (this.parent, *this.parent.parents):
        if (candidate / "recsys").is_dir() and (candidate / "data").is_dir():
            return candidate
    return Path.cwd().resolve()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="导出 Two-Tower embeddings")
    p.add_argument(
        "--config",
        default="configs/two_tower/config_local.yaml",
        help="训练时使用的 YAML 配置文件路径（相对 recsys/ 或绝对路径）",
    )
    p.add_argument(
        "--checkpoint",
        default="best",
        help="要载入的 checkpoint，支持 'best'|'last' 或自定义路径/URI",
    )
    return p


def _resolve_config_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    if p.is_absolute() and p.exists():
        return p.resolve()
    candidates = [
        Path.cwd() / raw,
        Path(__file__).resolve().parent / raw,
        _detect_workspace_root() / raw,
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise FileNotFoundError(f"找不到配置文件: {raw}")


def _resolve_ckpt_path(checkpoint_dir: str, resume_from: str) -> str:
    rf = resume_from.strip().lower()
    if rf in ("", "last"):
        return checkpoint_dir.rstrip("/") + "/last_model.pt"
    if rf == "best":
        return checkpoint_dir.rstrip("/") + "/best_model.pt"
    return resume_from


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    config_path = _resolve_config_path(args.config)
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg: TrainingConfig = parse_config(raw)

    workspace_root = _detect_workspace_root()
    backend = create_backend(
        cfg.environment, workspace_root=workspace_root, cloud_config=cfg.cloud
    )

    print(f"[Export] 使用配置: {config_path}")

    # 读取数据结构以获得 num_users/num_items 与映射
    _, _, data_summary = load_datasets(
        backend,
        train_csv=cfg.paths.train_interactions_csv,
        test_csv=cfg.paths.test_interactions_csv,
        train_params=cfg.train_params,
        seed=cfg.seed,
    )

    device = resolve_device(cfg.train_params.device)
    model = build_model(
        cfg.model_params,
        num_users=data_summary.num_users,
        num_items=data_summary.num_items,
    )

    ckpt_path = _resolve_ckpt_path(cfg.paths.checkpoint_dir, args.checkpoint)
    if not backend.exists(ckpt_path):
        raise FileNotFoundError(f"找不到 checkpoint: {ckpt_path}")

    print(f"[Export] 加载 checkpoint: {ckpt_path}")
    ckpt = backend.load_checkpoint(ckpt_path, map_location=str(device))
    model.load_state_dict(
        ckpt["model_state_dict"]
    ) if "model_state_dict" in ckpt else model.load_state_dict(ckpt)
    model = model.to(device)
    model.eval()

    # 导出 embedding
    num_users = data_summary.num_users
    num_items = data_summary.num_items
    embedding_dir = cfg.paths.embedding_dir
    backend.makedirs(embedding_dir)

    import torch

    with torch.no_grad():
        u_ids = torch.arange(num_users, device=device, dtype=torch.long)
        i_ids = torch.arange(num_items, device=device, dtype=torch.long)
        u_emb = model.encode_user(u_ids).cpu()
        i_emb = model.encode_item(i_ids).cpu()

    print(f"[Export] 保存 embeddings 至: {embedding_dir}")
    backend.save_tensor(u_emb, embedding_dir.rstrip("/") + "/user_embeddings.pt")
    backend.save_tensor(i_emb, embedding_dir.rstrip("/") + "/item_embeddings.pt")
    backend.save_json(
        data_summary.user_to_idx, embedding_dir.rstrip("/") + "/user_index.json"
    )
    backend.save_json(
        data_summary.item_to_idx, embedding_dir.rstrip("/") + "/item_index.json"
    )

    print("[Export] 导出完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
