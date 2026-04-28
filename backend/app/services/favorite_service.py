"""用户收藏业务服务。"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Sequence

from fastapi import HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.song import Song
from app.models.user_favorite import UserFavorite
from app.schemas.music import (
    FavoriteListResponse,
    FavoriteToggleResponse,
    FavoriteTrackResponse,
)
from app.services.track_mapper import to_track_response


async def fetch_liked_song_ids(
    db: AsyncSession,
    *,
    user_id: int,
    song_ids: Sequence[int],
) -> set[int]:
    """批量读取当前用户已收藏的歌曲主键集合。"""

    unique_song_ids = list(dict.fromkeys(int(song_id) for song_id in song_ids))
    if not unique_song_ids:
        return set()

    stmt = select(UserFavorite.song_id).where(
        UserFavorite.user_id == user_id,
        UserFavorite.song_id.in_(unique_song_ids),
    )
    rows = await db.scalars(stmt)
    return {int(song_id) for song_id in rows.all()}


class FavoriteService:
    """收藏切换与列表查询服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def toggle_favorite(
        self,
        *,
        user_id: int,
        song_id: int,
    ) -> FavoriteToggleResponse:
        """切换指定歌曲的收藏状态。"""

        song = await self.db.get(Song, song_id)
        if song is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="歌曲不存在",
            )

        favorite_stmt = select(UserFavorite.id).where(
            UserFavorite.user_id == user_id,
            UserFavorite.song_id == song.id,
        )
        existing_favorite_id = await self.db.scalar(favorite_stmt)
        if existing_favorite_id is not None:
            await self.db.execute(
                delete(UserFavorite).where(
                    UserFavorite.user_id == user_id,
                    UserFavorite.song_id == song.id,
                )
            )
            await self.db.commit()
            return FavoriteToggleResponse(
                song_id=song_id,
                is_liked=False,
                detail="已取消收藏",
            )

        self.db.add(
            UserFavorite(
                user_id=user_id,
                song_id=song.id,
                favorited_at=datetime.now(timezone.utc),
            )
        )
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            return FavoriteToggleResponse(
                song_id=song_id,
                is_liked=True,
                detail="收藏成功",
            )

        return FavoriteToggleResponse(
            song_id=song_id,
            is_liked=True,
            detail="收藏成功",
        )

    async def get_favorite_list(
        self,
        *,
        user_id: int,
        limit: int,
        offset: int,
    ) -> FavoriteListResponse:
        """分页读取当前用户收藏的歌曲列表。"""

        query_limit = limit + 1
        stmt = (
            select(
                UserFavorite.favorited_at,
                Song.id,
                Song.song_id,
                Song.name,
                Song.artist_name,
                Song.song_length,
            )
            .join(Song, Song.id == UserFavorite.song_id)
            .where(UserFavorite.user_id == user_id)
            .order_by(UserFavorite.favorited_at.desc(), UserFavorite.id.desc())
            .limit(query_limit)
            .offset(offset)
        )
        rows = (await self.db.execute(stmt)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]

        items: list[FavoriteTrackResponse] = []
        for (
            favorited_at,
            song_pk,
            song_value,
            song_name,
            artist_name,
            song_length,
        ) in rows:
            base_track = to_track_response(
                song_pk=int(song_pk),
                song_id=str(song_value),
                name=song_name,
                artist_name=artist_name,
                song_length=song_length,
                is_liked=True,
            )
            items.append(
                FavoriteTrackResponse(
                    **base_track.model_dump(),
                    favorited_at=favorited_at,
                )
            )

        return FavoriteListResponse(
            limit=limit,
            offset=offset,
            has_more=has_more,
            items=items,
        )
