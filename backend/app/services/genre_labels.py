"""流派名称映射与展示辅助。"""

from __future__ import annotations

KNOWN_GENRE_LABELS: dict[str, str] = {
    "3": "民谣",
    "465": "流行",
    "786": "华语流行",
    "798": "摇滚",
    "1609": "电子舞曲",
    "2122": "爵士",
}


def format_genre_name(genre_code: str) -> str:
    """将流派编码转换为可读名称。"""

    normalized_code = genre_code.strip()
    if not normalized_code:
        return "未知流派"
    return KNOWN_GENRE_LABELS.get(normalized_code, f"流派 {normalized_code}")
