"""音乐播放与推荐相关响应模型。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TrackResponse(BaseModel):
    """前端音乐列表统一曲目结构。"""

    id: int
    song_id: str
    name: str
    artist: str
    album: str
    cover_url: str
    duration_ms: int


class SongDetailResponse(TrackResponse):
    """单曲详情。"""

    language: float | None = None
    audio_object_key: str | None = None


class SongStreamResponse(BaseModel):
    """单曲可播放流地址响应。"""

    song_id: int
    stream_url: str
    expires_in_seconds: int
    strategy: Literal["minio_presigned_url"] = "minio_presigned_url"


class HotRecommendationsResponse(BaseModel):
    """全局热门推荐分页响应。"""

    model_config = ConfigDict(extra="forbid")

    strategy: Literal["global_hot"] = "global_hot"
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    items: list[TrackResponse]
