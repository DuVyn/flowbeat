"""歌曲播放相关接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import RedirectResponse
from minio import Minio
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.cache import get_redis_client
from app.core.storage import get_minio_client
from app.db.session import get_db_session
from app.schemas.music import (
    SongCoversRequest,
    SongCoversResponse,
    SongDetailResponse,
    SongFeedResponse,
    SongSearchResponse,
    SongStreamResponse,
)
from app.services.song_service import SongService

router = APIRouter(prefix="/api/songs", tags=["songs"])


@router.get("/search", response_model=SongSearchResponse)
async def search_songs(
    query: str = Query(alias="q", min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
    redis_client: Redis = Depends(get_redis_client),
) -> SongSearchResponse:
    """按关键词搜索歌曲。"""
    service = SongService(db, redis_client=redis_client)
    return await service.search_songs(query=query, limit=limit, offset=offset)


@router.get("/latest", response_model=SongFeedResponse)
async def get_latest_songs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> SongFeedResponse:
    """获取最近入库的歌曲。"""

    service = SongService(db)
    return await service.get_latest_songs(limit=limit, offset=offset)


@router.get("/{song_id}/detail", response_model=SongDetailResponse)
async def get_song_detail(
    song_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> SongDetailResponse:
    """获取单首歌曲详情。"""
    service = SongService(db)
    return await service.get_song_detail(song_id)


@router.get("/{song_id}/stream", response_model=SongStreamResponse)
async def get_song_stream(
    song_id: int,
    db: AsyncSession = Depends(get_db_session),
    minio_client: Minio = Depends(get_minio_client),
) -> SongStreamResponse:
    """获取单首歌曲可播放流地址。"""
    service = SongService(db, minio_client=minio_client)
    return await service.get_song_stream(song_id)


@router.post("/covers", response_model=SongCoversResponse)
async def get_song_covers(
    payload: SongCoversRequest,
    db: AsyncSession = Depends(get_db_session),
    minio_client: Minio = Depends(get_minio_client),
    redis_client: Redis = Depends(get_redis_client),
) -> SongCoversResponse:
    """批量获取歌曲封面预签名地址。"""
    service = SongService(db, minio_client=minio_client, redis_client=redis_client)
    return await service.get_song_covers_batch(payload.song_ids)


@router.get("/{song_id}/cover", response_class=RedirectResponse)
async def get_song_cover(
    song_id: int,
    db: AsyncSession = Depends(get_db_session),
    minio_client: Minio = Depends(get_minio_client),
) -> RedirectResponse:
    """获取单首歌曲封面跳转地址。"""
    service = SongService(db, minio_client=minio_client)
    cover_url = await service.get_song_cover(song_id)
    return RedirectResponse(url=cover_url, status_code=307)
