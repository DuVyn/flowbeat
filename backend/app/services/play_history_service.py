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
from app.services.favorite_service import fetch_liked_song_ids
from app.services.track_mapper import to_track_response


class PlayHistoryService:
    """用户播放历史写入与查询服务。"""

    def __init__(self, db: AsyncSession, *, user_id: int | None = None):
        self.db = db
        self.user_id = user_id

    async def _apply_liked_flags(self, tracks: list) -> list:
        """按当前用户收藏关系补充曲目收藏状态。"""

        user_id = self.user_id
        if user_id is None or not tracks:
            return tracks

        liked_song_ids = await fetch_liked_song_ids(
            self.db,
            user_id=user_id,
            song_ids=[track.id for track in tracks],
        )
        return [
            track.model_copy(update={"is_liked": track.id in liked_song_ids})
            for track in tracks
        ]

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
                is_liked=False,
            )
            items.append(
                PlayHistoryItemResponse(
                    **base_track.model_dump(),
                    played_at=played_at,
                )
            )

        items = await self._apply_liked_flags(items)

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
            is_liked=False,
        )
        item = PlayHistoryItemResponse(
            **base_track.model_dump(),
            played_at=played_at,
        )
        flagged_items = await self._apply_liked_flags([item])
        return flagged_items[0]

    async def clear_play_history(self, *, user_id: int) -> ClearPlayHistoryResponse:
        """清空当前用户的播放历史。"""

        result = await self.db.execute(
            delete(PlayHistory).where(PlayHistory.user_id == user_id)
        )
        await self.db.commit()
        deleted_count = int(getattr(result, "rowcount", 0) or 0)
        return ClearPlayHistoryResponse(deleted_count=deleted_count)
