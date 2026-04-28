"""流派目录与分类歌曲服务。"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.associations import song_genre_m2m
from app.models.play_count import PlayCount
from app.models.song import Song
from app.models.song_meta import Genre
from app.schemas.music import (
    GenreCatalogItemResponse,
    GenreCatalogResponse,
    SongFeedResponse,
)
from app.services.favorite_service import fetch_liked_song_ids
from app.services.genre_labels import format_genre_name
from app.services.track_mapper import to_track_response


class GenreService:
    """流派目录与流派歌曲读取服务。"""

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

    async def get_genre_catalog(self) -> GenreCatalogResponse:
        """返回所有已入库流派及其关联歌曲数量。"""

        stmt = (
            select(
                Genre.genre_code,
                func.count(song_genre_m2m.c.song_id).label("song_count"),
            )
            .outerjoin(song_genre_m2m, song_genre_m2m.c.genre_id == Genre.id)
            .group_by(Genre.id, Genre.genre_code)
            .order_by(
                func.count(song_genre_m2m.c.song_id).desc(), Genre.genre_code.asc()
            )
        )
        rows = (await self.db.execute(stmt)).all()
        items = [
            GenreCatalogItemResponse(
                genre_code=str(row.genre_code),
                genre_name=format_genre_name(str(row.genre_code)),
                song_count=int(row.song_count),
            )
            for row in rows
        ]
        return GenreCatalogResponse(items=items)

    async def get_genre_songs(
        self,
        *,
        genre_code: str,
        limit: int,
        offset: int,
    ) -> SongFeedResponse:
        """按流派编码读取歌曲列表。"""

        normalized_code = genre_code.strip()
        query_limit = limit + 1
        genre_name = format_genre_name(normalized_code)

        stmt = (
            select(
                Song.id,
                Song.song_id,
                Song.name,
                Song.artist_name,
                Song.song_length,
            )
            .join(song_genre_m2m, song_genre_m2m.c.song_id == Song.id)
            .join(Genre, Genre.id == song_genre_m2m.c.genre_id)
            .outerjoin(PlayCount, PlayCount.song_id == Song.id)
            .where(Genre.genre_code == normalized_code)
            .order_by(PlayCount.total_play_count.desc(), Song.id.desc())
            .limit(query_limit)
            .offset(offset)
        )
        rows = (await self.db.execute(stmt)).all()
        has_more = len(rows) > limit
        rows = rows[:limit]

        items = [
            to_track_response(
                song_pk=int(row.id),
                song_id=str(row.song_id),
                name=row.name,
                artist_name=row.artist_name,
                song_length=row.song_length,
                is_liked=False,
            )
            for row in rows
        ]
        items = await self._apply_liked_flags(items)

        return SongFeedResponse(
            title=f"{genre_name}歌曲",
            limit=limit,
            offset=offset,
            has_more=has_more,
            genre_code=normalized_code,
            genre_name=genre_name,
            items=items,
        )
