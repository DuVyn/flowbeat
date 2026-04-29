"""双塔模型训练主入口（配置驱动，支持云端读数据、服务器本地落盘）。

用法:
    cd recsys
    uv run python train_two_tower.py --config configs/two_tower/config_local.yaml
    uv run python train_two_tower.py --config configs/two_tower/config_cloud.yaml
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from training.two_tower.config_schema import TrainingConfig, parse_config
from training.two_tower.data_engine import load_datasets
from training.two_tower.model_builder import build_model, resolve_device
from training.two_tower.storage_backend import create_backend
from training.two_tower.trainer import train

CURRENT_FILE = Path(__file__).resolve()
RECSYS_ROOT = CURRENT_FILE.parent


def _detect_workspace_root() -> Path:
    for candidate in (RECSYS_ROOT, *RECSYS_ROOT.parents):
        if (candidate / "recsys").is_dir() and (candidate / "data").is_dir():
            return candidate
    return Path.cwd().resolve()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="FlowBeat Two-Tower 双塔模型训练",
    )
    parser.add_argument(
        "--config",
        default="configs/two_tower/config_local.yaml",
        help="YAML 配置文件路径（相对于 recsys/ 或绝对路径）",
    )
    return parser


def _resolve_config_path(raw: str) -> Path:
    p = Path(raw).expanduser()
    if p.is_absolute() and p.exists():
        return p.resolve()
    candidates = [
        Path.cwd() / raw,
        RECSYS_ROOT / raw,
        _detect_workspace_root() / raw,
        RECSYS_ROOT / "configs" / "two_tower" / Path(raw).name,
    ]
    for c in candidates:
        if c.exists():
            return c.resolve()
    raise FileNotFoundError(f"找不到配置文件: {raw}")


def run(cfg: TrainingConfig, workspace_root: Path) -> dict[str, Any]:
    """根据配置执行完整训练流程。"""
    backend = create_backend(
        cfg.environment,
        workspace_root=workspace_root,
        cloud_config=cfg.cloud,
    )

    train_loader, test_loader, data_summary = load_datasets(
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

    result = train(
        model=model,
        train_loader=train_loader,
        test_loader=test_loader,
        train_params=cfg.train_params,
        backend=backend,
        checkpoint_dir=cfg.paths.checkpoint_dir,
        embedding_dir=cfg.paths.embedding_dir,
        report_dir=cfg.paths.report_dir,
        user_to_idx=data_summary.user_to_idx,
        item_to_idx=data_summary.item_to_idx,
        num_users=data_summary.num_users,
        num_items=data_summary.num_items,
        seed=cfg.seed,
        device=device,
    )

    return asdict(result)


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    config_path = _resolve_config_path(args.config)
    print(f"[Main] 配置文件: {config_path}", flush=True)

    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    cfg = parse_config(raw)

    print(f"[Main] 运行环境: {cfg.environment}", flush=True)
    print(f"[Main] 随机种子: {cfg.seed}", flush=True)

    workspace_root = _detect_workspace_root()
    print(f"[Main] 工作区根: {workspace_root}", flush=True)

    try:
        summary = run(cfg, workspace_root)
    except KeyboardInterrupt:
        print("\n[Main] 训练已被 Ctrl+C 中断。", flush=True)
        raise SystemExit(130)

    print("\n" + "=" * 60, flush=True)
    print("训练结果摘要:", flush=True)
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
