"""音乐播放与推荐相关响应模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RecommendationStrategy = Literal["two_tower", "content_cold_start", "global_hot"]


class TrackResponse(BaseModel):
    """前端音乐列表统一曲目结构。"""

    id: int
    song_id: str
    name: str
    artist: str
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


class PersonalizedRecommendationsResponse(BaseModel):
    """个性化推荐分页响应。"""

    model_config = ConfigDict(extra="forbid")

    strategy: RecommendationStrategy
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    total: int = Field(ge=0)
    items: list[TrackResponse]


class SongSearchResponse(BaseModel):
    """歌曲搜索分页响应。"""

    model_config = ConfigDict(extra="forbid")

    query: str
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool
    items: list[TrackResponse]


class SongCoversRequest(BaseModel):
    """批量封面地址请求。"""

    model_config = ConfigDict(extra="forbid")

    song_ids: list[int] = Field(min_length=1, max_length=100)


class SongCoversResponse(BaseModel):
    """批量封面地址响应。"""

    covers: dict[int, str]


class RecordPlayHistoryRequest(BaseModel):
    """记录播放历史请求。"""

    model_config = ConfigDict(extra="forbid")

    song_id: int = Field(gt=0)


class RecordPlayHistoryResponse(BaseModel):
    """记录播放历史响应。"""

    detail: str = "记录成功"


class PlayHistoryItemResponse(TrackResponse):
    """播放历史条目。"""

    played_at: datetime


class PlayHistoryResponse(BaseModel):
    """播放历史分页响应。"""

    model_config = ConfigDict(extra="forbid")

    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool
    items: list[PlayHistoryItemResponse]


class GenrePreferenceItemResponse(BaseModel):
    """用户流派偏好条目。"""

    genre_code: str
    genre_name: str
    play_count: int
    weight: float


class ListeningInsightsResponse(BaseModel):
    """首页偏好雷达图数据。"""

    model_config = ConfigDict(extra="forbid")

    total_plays: int
    total_distinct_genres: int
    items: list[GenrePreferenceItemResponse]


class GenreCatalogItemResponse(BaseModel):
    """流派目录条目。"""

    genre_code: str
    genre_name: str
    song_count: int


class GenreCatalogResponse(BaseModel):
    """流派目录列表响应。"""

    model_config = ConfigDict(extra="forbid")

    items: list[GenreCatalogItemResponse]


class SongFeedResponse(BaseModel):
    """通用歌曲列表响应。"""

    model_config = ConfigDict(extra="forbid")

    title: str
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)
    has_more: bool
    genre_code: str | None = None
    genre_name: str | None = None
    items: list[TrackResponse]


class ClearPlayHistoryResponse(BaseModel):
    """清空播放历史响应。"""

    detail: str = "清空成功"
    deleted_count: int = Field(ge=0)
