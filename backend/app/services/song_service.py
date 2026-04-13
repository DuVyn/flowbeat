"""歌曲播放相关业务服务。"""

from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from minio import Minio
from minio.error import S3Error
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.song import Song
from app.schemas.music import SongDetailResponse, SongStreamResponse, TrackResponse
from app.services.track_mapper import to_track_response


def build_track_response(
    *,
    song_pk: int,
    song_id: str,
    name: str | None,
    artist_name: str | None,
    song_length: int | None,
) -> TrackResponse:
    """兼容旧调用入口，实际映射委托给共享 mapper。"""
    return to_track_response(
        song_pk=song_pk,
        song_id=song_id,
        name=name,
        artist_name=artist_name,
        song_length=song_length,
    )


class SongService:
    """歌曲查询与可播放地址签发服务。"""

    def __init__(self, db: AsyncSession, minio_client: Minio | None = None):
        self.db = db
        self.minio_client = minio_client

    async def get_song_detail(self, song_id: int) -> SongDetailResponse:
        """根据歌曲主键获取详情。"""
        detail_stmt = select(
            Song.id,
            Song.song_id,
            Song.name,
            Song.artist_name,
            Song.song_length,
            Song.language,
            Song.audio_object_key,
        ).where(Song.id == song_id)
        row = (await self.db.execute(detail_stmt)).first()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="歌曲不存在",
            )

        base_track = build_track_response(
            song_pk=int(row.id),
            song_id=str(row.song_id),
            name=row.name,
            artist_name=row.artist_name,
            song_length=row.song_length,
        )
        return SongDetailResponse(
            **base_track.model_dump(),
            language=row.language,
            audio_object_key=row.audio_object_key,
        )

    async def get_song_stream(self, song_id: int) -> SongStreamResponse:
        """签发 MinIO 预签名播放地址。"""
        stream_stmt = select(Song.id, Song.audio_object_key).where(Song.id == song_id)
        row = (await self.db.execute(stream_stmt)).first()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="歌曲不存在",
            )
        if not row.audio_object_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该歌曲暂无可播放音频",
            )
        if self.minio_client is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="音频服务未初始化",
            )

        try:
            stream_url = await run_in_threadpool(
                self.minio_client.presigned_get_object,
                settings.minio_song_bucket,
                row.audio_object_key,
                expires=timedelta(seconds=settings.minio_presign_expires_seconds),
            )
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject"}:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="音频对象不存在：数据库对象键与 MinIO 对象名不一致",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="音频服务暂不可用，请稍后重试",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="音频服务网络异常，请稍后重试",
            ) from exc

        return SongStreamResponse(
            song_id=int(row.id),
            stream_url=stream_url,
            expires_in_seconds=settings.minio_presign_expires_seconds,
        )
