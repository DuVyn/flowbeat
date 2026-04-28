"""TrackResponse 映射工具。"""

from __future__ import annotations

from app.schemas.music import TrackResponse


def to_track_response(
    *,
    song_pk: int,
    song_id: str,
    name: str | None,
    artist_name: str | None,
    song_length: int | None,
    is_liked: bool = False,
) -> TrackResponse:
    """将歌曲基础字段转换为前端 Track 结构。"""
    return TrackResponse(
        id=song_pk,
        song_id=song_id,
        name=name or song_id,
        artist=artist_name or "未知艺术家",
        cover_url="",
        duration_ms=song_length or 0,
        is_liked=is_liked,
    )
