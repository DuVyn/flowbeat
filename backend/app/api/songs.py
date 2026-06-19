"""歌曲播放相关接口。"""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from minio import Minio
from minio.error import S3Error
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_auth_context
from app.core.cache import get_redis_client
from app.core.config import settings
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


def _stream_object_response(
    minio_client: Minio,
    *,
    bucket_name: str,
    object_key: str,
) -> StreamingResponse:
    """将 MinIO 对象包装成可直接给浏览器消费的流式响应。"""
    try:
        stat = minio_client.stat_object(bucket_name, object_key)
        object_stream = minio_client.get_object(bucket_name, object_key)
    except S3Error as exc:
        if exc.code in {"NoSuchKey", "NoSuchObject"}:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="对象不存在"
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="对象存储暂不可用，请稍后重试",
        ) from exc

    def chunk_iter() -> Iterator[bytes]:
        try:
            while True:
                chunk = object_stream.read(64 * 1024)
                if not chunk:
                    break
                yield chunk
        finally:
            object_stream.close()
            object_stream.release_conn()

    headers = {}
    if getattr(stat, "size", None) is not None:
        headers["Content-Length"] = str(stat.size)

    media_type = getattr(stat, "content_type", None) or "application/octet-stream"
    return StreamingResponse(chunk_iter(), media_type=media_type, headers=headers)


@router.get("/search", response_model=SongSearchResponse)
async def search_songs(
    query: str = Query(alias="q", min_length=1, max_length=100),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
    redis_client: Redis = Depends(get_redis_client),
) -> SongSearchResponse:
    """按关键词搜索歌曲。"""
    service = SongService(db, redis_client=redis_client, user_id=auth_context.user.id)
    return await service.search_songs(query=query, limit=limit, offset=offset)


@router.get("/latest", response_model=SongFeedResponse)
async def get_latest_songs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SongFeedResponse:
    """获取最近入库的歌曲。"""

    service = SongService(db, user_id=auth_context.user.id)
    return await service.get_latest_songs(limit=limit, offset=offset)


@router.get("/{song_id}/detail", response_model=SongDetailResponse)
async def get_song_detail(
    song_id: int,
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SongDetailResponse:
    """获取单首歌曲详情。"""
    service = SongService(db, user_id=auth_context.user.id)
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


@router.get("/{song_id}/stream/file")
async def stream_song_file(
    song_id: int,
    db: AsyncSession = Depends(get_db_session),
    minio_client: Minio = Depends(get_minio_client),
) -> StreamingResponse:
    """直接流式输出歌曲音频文件。"""
    service = SongService(db, minio_client=minio_client)
    stream_stmt = await service.get_song_detail(song_id)
    if not stream_stmt.audio_object_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该歌曲暂无可播放音频",
        )

    return _stream_object_response(
        minio_client,
        bucket_name=settings.minio_song_bucket,
        object_key=stream_stmt.audio_object_key,
    )


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


@router.get("/{song_id}/cover", response_class=StreamingResponse)
async def get_song_cover(
    song_id: int,
    db: AsyncSession = Depends(get_db_session),
    minio_client: Minio = Depends(get_minio_client),
) -> StreamingResponse:
    """直接流式输出单首歌曲封面。"""
    service = SongService(db, minio_client=minio_client)
    _ = await service.get_song_cover(song_id)
    cover_stmt = await service.get_song_detail(song_id)
    if not cover_stmt.audio_object_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="该歌曲暂无可展示封面",
        )

    cover_object_key = service._build_cover_object_key(cover_stmt.audio_object_key)
    return _stream_object_response(
        minio_client,
        bucket_name=settings.minio_song_bucket,
        object_key=cover_object_key,
    )
