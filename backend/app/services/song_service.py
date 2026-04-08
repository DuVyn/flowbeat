"""歌曲播放相关业务服务。"""

from __future__ import annotations

from datetime import timedelta

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from minio import Minio
from minio.error import S3Error
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.song import Song
from app.schemas.music import SongDetailResponse, SongStreamResponse, TrackResponse


def build_track_response(song: Song) -> TrackResponse:
    """将 Song ORM 对象映射为前端 Track 结构。"""
    return TrackResponse(
        id=song.id,
        song_id=song.song_id,
        name=song.name or song.song_id,
        artist=song.artist_name or "未知艺术家",
        album="未知专辑",
        cover_url="",
        duration_ms=song.song_length or 0,
    )


class SongService:
    """歌曲查询与可播放地址签发服务。"""

    def __init__(self, db: AsyncSession, minio_client: Minio | None = None):
        self.db = db
        self.minio_client = minio_client

    async def get_song_detail(self, song_id: int) -> SongDetailResponse:
        """根据歌曲主键获取详情。"""
        song = await self.db.get(Song, song_id)
        if song is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="歌曲不存在",
            )

        base_track = build_track_response(song)
        return SongDetailResponse(
            **base_track.model_dump(),
            language=song.language,
            audio_object_key=song.audio_object_key,
        )

    async def get_song_stream(self, song_id: int) -> SongStreamResponse:
        """签发 MinIO 预签名播放地址。"""
        song = await self.db.get(Song, song_id)
        if song is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="歌曲不存在",
            )
        if not song.audio_object_key:
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
            await run_in_threadpool(
                self.minio_client.stat_object,
                settings.minio_song_bucket,
                song.audio_object_key,
            )
            stream_url = await run_in_threadpool(
                self.minio_client.presigned_get_object,
                settings.minio_song_bucket,
                song.audio_object_key,
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

        return SongStreamResponse(
            song_id=song.id,
            stream_url=stream_url,
            expires_in_seconds=settings.minio_presign_expires_seconds,
        )
