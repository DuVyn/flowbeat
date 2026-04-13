from __future__ import annotations

import os
from pathlib import Path


def _is_within(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def detect_workspace_root(*, anchor_file: Path) -> Path:
    """根据环境变量与目录标记探测工作区根目录。"""
    env_root = os.getenv("FLOWBEAT_WORKSPACE_ROOT", "").strip()
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if candidate.exists():
            return candidate

    search_origins = [Path.cwd().resolve(), anchor_file.resolve()]
    for origin in search_origins:
        for candidate in (origin, *origin.parents):
            if (candidate / "recsys").is_dir() and (candidate / "data").is_dir():
                return candidate

    for candidate in (anchor_file.resolve(), *anchor_file.resolve().parents):
        if (candidate / "recsys").is_dir():
            return candidate

    return Path.cwd().resolve()


def resolve_workspace_path(
    path_text: str,
    *,
    workspace_root: Path,
    allow_external_paths: bool = False,
) -> Path:
    """基于工作区根目录解析路径，默认拒绝工作区外绝对路径。"""
    path = Path(path_text).expanduser()
    resolved = (
        path.resolve() if path.is_absolute() else (workspace_root / path).resolve()
    )

    if not allow_external_paths and not _is_within(resolved, workspace_root):
        raise ValueError(
            "路径位于工作区根目录之外。"
            "如确需放行，请将 allow_external_paths 设为 true："
            f"{resolved}"
        )

    return resolved


def resolve_existing_config_path(
    path_text: str,
    *,
    workspace_root: Path,
    recsys_root: Path,
    allow_external_paths: bool = True,
) -> Path:
    """从常见位置解析配置路径，并返回首个已存在的候选路径。"""
    path = Path(path_text).expanduser()
    if path.is_absolute():
        resolved = path.resolve()
        if not allow_external_paths and not _is_within(resolved, workspace_root):
            raise ValueError(f"配置路径位于工作区根目录之外: {resolved}")
        return resolved

    name_candidates = [path.name]
    if not path.suffix:
        name_candidates.append(f"{path.name}.json")

    candidates: list[Path] = [
        (Path.cwd() / path).resolve(),
        (recsys_root / path).resolve(),
        (workspace_root / path).resolve(),
    ]
    for name in name_candidates:
        candidates.extend(
            [
                (recsys_root / "configs" / "two_tower" / name).resolve(),
                (recsys_root / "configs" / name).resolve(),
                (workspace_root / "recsys" / "configs" / "two_tower" / name).resolve(),
            ]
        )

    for candidate in candidates:
        if candidate.exists():
            return candidate

    first = candidates[0]
    if not allow_external_paths and not _is_within(first, workspace_root):
        raise ValueError(f"解析后的配置路径位于工作区根目录之外: {first}")
    return first


def to_posix_relative(target: Path, *, base_dir: Path) -> str:
    """优先以相对路径保存产物路径，提升跨环境可移植性。"""
    try:
        relative = target.resolve().relative_to(base_dir.resolve())
        return relative.as_posix()
    except ValueError:
        return target.resolve().as_posix()
