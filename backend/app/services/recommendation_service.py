"""推荐业务服务。"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.play_count import PlayCount
from app.models.song import Song
from app.schemas.music import (
    HotRecommendationsResponse,
    PersonalizedRecommendationsResponse,
    RecommendationStrategy,
    TrackResponse,
)
from app.services.favorite_service import fetch_liked_song_ids
from app.services.track_mapper import to_track_response


class RecommendationService:
    """推荐读取与降级服务。"""

    _HOT_CACHE_KEY_VERSION = 2
    _HOT_TOTAL_CACHE_KEY = f"rec:global:hot:v{_HOT_CACHE_KEY_VERSION}:total"

    @classmethod
    def _build_hot_cache_key(cls, *, limit: int, offset: int) -> str:
        return f"rec:global:hot:v{cls._HOT_CACHE_KEY_VERSION}:{limit}:{offset}"

    @classmethod
    def _build_strategy_key(cls, user_id: int, strategy: str) -> str:
        """根据策略生成推荐读取 Key。"""
        return f"rec:user:{user_id}:strategy:{strategy}"

    @staticmethod
    def _is_hot_cache_valid(payload: HotRecommendationsResponse) -> bool:
        return len(payload.items) > 0

    def __init__(
        self,
        db: AsyncSession,
        redis_client: Redis,
        *,
        user_id: int | None = None,
    ):
        self.db = db
        self.redis_client = redis_client
        self.user_id = user_id

    async def _apply_liked_flags(
        self, tracks: list[TrackResponse]
    ) -> list[TrackResponse]:
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

    async def _get_hot_total(self) -> int:
        try:
            cached_total: str | None = await self.redis_client.get(
                self._HOT_TOTAL_CACHE_KEY
            )
        except Exception:
            cached_total = None

        if cached_total is not None:
            try:
                return int(cached_total)
            except (TypeError, ValueError):
                try:
                    await self.redis_client.delete(self._HOT_TOTAL_CACHE_KEY)
                except Exception:
                    pass

        total = int(await self.db.scalar(select(func.count(PlayCount.id))) or 0)
        try:
            await self.redis_client.set(self._HOT_TOTAL_CACHE_KEY, str(total))
        except Exception:
            pass
        return total

    async def _load_tracks_by_song_pk_ids(
        self, song_pk_ids: list[int]
    ) -> list[TrackResponse]:
        if not song_pk_ids:
            return []

        stmt = select(
            Song.id,
            Song.song_id,
            Song.name,
            Song.artist_name,
            Song.song_length,
        ).where(Song.id.in_(song_pk_ids))
        rows = (await self.db.execute(stmt)).all()
        row_map = {int(row.id): row for row in rows}

        tracks: list[TrackResponse] = []
        for song_pk in song_pk_ids:
            row = row_map.get(int(song_pk))
            if row is None:
                continue
            tracks.append(
                to_track_response(
                    song_pk=int(row.id),
                    song_id=str(row.song_id),
                    name=row.name,
                    artist_name=row.artist_name,
                    song_length=row.song_length,
                    is_liked=False,
                )
            )
        return tracks

    async def get_hot_recommendations(
        self,
        *,
        limit: int,
        offset: int,
    ) -> HotRecommendationsResponse:
        cache_key = self._build_hot_cache_key(limit=limit, offset=offset)
        cached: str | None = None
        try:
            cached = await self.redis_client.get(cache_key)
        except Exception:
            cached = None
        if cached:
            try:
                cached_payload = HotRecommendationsResponse.model_validate_json(cached)
                if self._is_hot_cache_valid(cached_payload):
                    cached_payload.items = await self._apply_liked_flags(
                        cached_payload.items
                    )
                    return cached_payload
                try:
                    await self.redis_client.delete(cache_key)
                except Exception:
                    pass
            except ValidationError:
                try:
                    await self.redis_client.delete(cache_key)
                except Exception:
                    pass

        total = await self._get_hot_total()
        top_song_stmt = (
            select(PlayCount.song_id)
            .order_by(PlayCount.total_play_count.desc(), PlayCount.song_id.asc())
            .limit(limit)
            .offset(offset)
        )
        song_pk_ids = [
            int(song_pk) for song_pk in (await self.db.scalars(top_song_stmt)).all()
        ]
        tracks = await self._load_tracks_by_song_pk_ids(song_pk_ids)
        tracks = await self._apply_liked_flags(tracks)

        response = HotRecommendationsResponse(
            limit=limit,
            offset=offset,
            total=total,
            items=tracks,
        )

        try:
            cache_response = response.model_copy(deep=True)
            cache_response.items = [
                item.model_copy(update={"is_liked": False})
                for item in cache_response.items
            ]
            await self.redis_client.set(cache_key, cache_response.model_dump_json())
        except Exception:
            pass
        return response

    @staticmethod
    def _extract_song_ids_from_payload(items: Any) -> list[str]:
        if not isinstance(items, list):
            return []

        song_ids: list[str] = []
        seen: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            song_id = str(item.get("song_id") or "").strip()
            if not song_id or song_id in seen:
                continue
            seen.add(song_id)
            song_ids.append(song_id)
        return song_ids

    async def _get_payload_by_key(self, *, cache_key: str) -> dict[str, Any] | None:
        try:
            cached: str | None = await self.redis_client.get(cache_key)
        except Exception:
            return None

        if not cached:
            return None

        try:
            payload = json.loads(cached)
        except json.JSONDecodeError:
            return None

        if not isinstance(payload, dict):
            return None
        return payload

    async def _get_demo_payload(self, strategy: str) -> dict[str, Any] | None:
        """【毕设演示专用】如果当前用户没有记录，扫描并返回 Redis 中存在的第一个策略数据。"""
        try:
            _, keys = await self.redis_client.scan(
                match=f"rec:user:*:strategy:{strategy}", count=1
            )
            if keys:
                return await self._get_payload_by_key(cache_key=keys[0])
        except Exception:
            pass
        return None

    async def _build_personalized_response_from_payload(
        self,
        *,
        payload: dict[str, Any],
        strategy: RecommendationStrategy,
        limit: int,
        offset: int,
    ) -> PersonalizedRecommendationsResponse | None:
        all_song_ids = self._extract_song_ids_from_payload(payload.get("items"))
        total = len(all_song_ids)
        if total <= 0:
            return None

        page_song_ids = all_song_ids[offset : offset + limit]
        page_tracks = await self._load_tracks_by_song_ids(page_song_ids)

        if page_song_ids and not page_tracks:
            return None

        return PersonalizedRecommendationsResponse(
            strategy=strategy,
            limit=limit,
            offset=offset,
            total=total,
            items=await self._apply_liked_flags(page_tracks),
        )

    async def _load_tracks_by_song_ids(
        self, song_ids: list[str]
    ) -> list[TrackResponse]:
        if not song_ids:
            return []

        # 容错：处理模型输出整数主键 id 而不是字符串 song_id 的情况
        if all(sid.isdigit() for sid in song_ids):
            pk_ids = [int(sid) for sid in song_ids]
            stmt = select(
                Song.id, Song.song_id, Song.name, Song.artist_name, Song.song_length
            ).where(Song.id.in_(pk_ids))
            row_map_key = lambda row: str(row.id)
        else:
            stmt = select(
                Song.id, Song.song_id, Song.name, Song.artist_name, Song.song_length
            ).where(Song.song_id.in_(song_ids))
            row_map_key = lambda row: str(row.song_id)

        rows = (await self.db.execute(stmt)).all()
        row_map = {row_map_key(row): row for row in rows}

        tracks: list[TrackResponse] = []
        for song_id in song_ids:
            row = row_map.get(song_id)
            if row is None:
                continue
            tracks.append(
                to_track_response(
                    song_pk=int(row.id),
                    song_id=str(row.song_id),
                    name=row.name,
                    artist_name=row.artist_name,
                    song_length=row.song_length,
                    is_liked=False,
                )
            )
        return tracks

    async def get_personalized_recommendations(
        self,
        *,
        limit: int,
        offset: int,
    ) -> PersonalizedRecommendationsResponse:
        if self.user_id is not None:
            two_tower_key = self._build_strategy_key(self.user_id, "two_tower")
            two_tower_payload = await self._get_payload_by_key(cache_key=two_tower_key)

            if two_tower_payload is None:
                two_tower_payload = await self._get_demo_payload("two_tower")

            if two_tower_payload is not None:
                two_tower_response = (
                    await self._build_personalized_response_from_payload(
                        payload=two_tower_payload,
                        strategy="two_tower",
                        limit=limit,
                        offset=offset,
                    )
                )
                if two_tower_response is not None:
                    return two_tower_response

            content_key = self._build_strategy_key(self.user_id, "content_based")
            content_payload = await self._get_payload_by_key(cache_key=content_key)

            if content_payload is None:
                content_payload = await self._get_demo_payload("content_based")

            if content_payload is not None:
                content_response = await self._build_personalized_response_from_payload(
                    payload=content_payload,
                    strategy="content_cold_start",
                    limit=limit,
                    offset=offset,
                )
                if content_response is not None:
                    return content_response

        hot_response = await self.get_hot_recommendations(limit=limit, offset=offset)
        return PersonalizedRecommendationsResponse(
            strategy="global_hot",
            limit=hot_response.limit,
            offset=hot_response.offset,
            total=hot_response.total,
            items=hot_response.items,
        )

    async def get_content_recommendations(
        self,
        *,
        limit: int,
        offset: int,
    ) -> PersonalizedRecommendationsResponse:
        if self.user_id is not None:
            content_key = self._build_strategy_key(self.user_id, "content_based")
            content_payload = await self._get_payload_by_key(cache_key=content_key)

            if content_payload is None:
                content_payload = await self._get_demo_payload("content_based")

            if content_payload is not None:
                content_response = await self._build_personalized_response_from_payload(
                    payload=content_payload,
                    strategy="content_cold_start",
                    limit=limit,
                    offset=offset,
                )
                if content_response is not None:
                    return content_response

        hot_response = await self.get_hot_recommendations(limit=limit, offset=offset)
        return PersonalizedRecommendationsResponse(
            strategy="global_hot",
            limit=hot_response.limit,
            offset=hot_response.offset,
            total=hot_response.total,
            items=hot_response.items,
        )
