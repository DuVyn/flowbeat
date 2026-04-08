"""播放历史相关业务服务。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.play_history import PlayHistory
from app.models.song import Song
from app.schemas.music import (
    PlayHistoryItemResponse,
    PlayHistoryResponse,
    RecordPlayHistoryRequest,
    RecordPlayHistoryResponse,
)


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
            .order_by(PlayHistory.played_at.desc())
            .limit(query_limit)
            .offset(offset)
        )
        rows = (await self.db.execute(query_stmt)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]

        items: list[PlayHistoryItemResponse] = []
        for played_at, song_pk, song_id, song_name, artist_name, song_length in rows:
            items.append(
                PlayHistoryItemResponse(
                    id=song_pk,
                    song_id=song_id,
                    name=song_name or song_id,
                    artist=artist_name or "未知艺术家",
                    album="未知专辑",
                    cover_url="",
                    duration_ms=song_length or 0,
                    played_at=played_at,
                )
            )

        return PlayHistoryResponse(
            limit=limit,
            offset=offset,
            has_more=has_more,
            items=items,
        )
