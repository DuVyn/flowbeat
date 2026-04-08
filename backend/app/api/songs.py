"""歌曲播放相关接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from minio import Minio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import get_minio_client
from app.db.session import get_db_session
from app.schemas.music import SongDetailResponse, SongStreamResponse
from app.services.song_service import SongService

router = APIRouter(prefix="/api/songs", tags=["songs"])


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
    service = SongService(db, minio_client)
    return await service.get_song_stream(song_id)
