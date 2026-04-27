"""播放历史相关业务服务。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.play_history import PlayHistory
from app.models.song import Song
from app.schemas.music import (
    ClearPlayHistoryResponse,
    PlayHistoryItemResponse,
    PlayHistoryResponse,
    RecordPlayHistoryRequest,
    RecordPlayHistoryResponse,
)
from app.services.track_mapper import to_track_response


class PlayHistoryService:
    """用户播放历史写入与查询服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def record_play_history(
        self,
        *,
        user_id: int,
        payload: RecordPlayHistoryRequest,
    ) -> RecordPlayHistoryResponse:
        """记录一次播放行为。"""
        song = await self.db.get(Song, payload.song_id)
        if song is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="歌曲不存在",
            )

        self.db.add(
            PlayHistory(
                user_id=user_id,
                song_id=song.id,
                played_at=datetime.now(timezone.utc),
            )
        )
        await self.db.commit()
        return RecordPlayHistoryResponse()

    async def get_play_history(
        self,
        *,
        user_id: int,
        limit: int,
        offset: int,
    ) -> PlayHistoryResponse:
        """分页读取当前用户最近播放历史。"""
        query_limit = limit + 1
        query_stmt = (
            select(
                PlayHistory.played_at,
                Song.id,
                Song.song_id,
                Song.name,
                Song.artist_name,
                Song.song_length,
            )
            .join(Song, Song.id == PlayHistory.song_id)
            .where(PlayHistory.user_id == user_id)
            .order_by(PlayHistory.played_at.desc(), PlayHistory.id.desc())
            .limit(query_limit)
            .offset(offset)
        )
        rows = (await self.db.execute(query_stmt)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]

        items: list[PlayHistoryItemResponse] = []
        for played_at, song_pk, song_id, song_name, artist_name, song_length in rows:
            base_track = to_track_response(
                song_pk=int(song_pk),
                song_id=str(song_id),
                name=song_name,
                artist_name=artist_name,
                song_length=song_length,
            )
            items.append(
                PlayHistoryItemResponse(
                    **base_track.model_dump(),
                    played_at=played_at,
                )
            )

        return PlayHistoryResponse(
            limit=limit,
            offset=offset,
            has_more=has_more,
            items=items,
        )

    async def get_latest_play_history(
        self,
        *,
        user_id: int,
    ) -> PlayHistoryItemResponse | None:
        """获取当前用户最近一次播放记录。"""

        latest_stmt = (
            select(
                PlayHistory.played_at,
                Song.id,
                Song.song_id,
                Song.name,
                Song.artist_name,
                Song.song_length,
            )
            .join(Song, Song.id == PlayHistory.song_id)
            .where(PlayHistory.user_id == user_id)
            .order_by(PlayHistory.played_at.desc(), PlayHistory.id.desc())
            .limit(1)
        )
        row = (await self.db.execute(latest_stmt)).first()
        if row is None:
            return None

        played_at, song_pk, song_id, song_name, artist_name, song_length = row
        base_track = to_track_response(
            song_pk=int(song_pk),
            song_id=str(song_id),
            name=song_name,
            artist_name=artist_name,
            song_length=song_length,
        )
        return PlayHistoryItemResponse(
            **base_track.model_dump(),
            played_at=played_at,
        )

    async def clear_play_history(self, *, user_id: int) -> ClearPlayHistoryResponse:
        """清空当前用户的播放历史。"""

        result = await self.db.execute(
            delete(PlayHistory).where(PlayHistory.user_id == user_id)
        )
        await self.db.commit()
        deleted_count = int(getattr(result, "rowcount", 0) or 0)
        return ClearPlayHistoryResponse(deleted_count=deleted_count)
