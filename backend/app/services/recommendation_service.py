"""推荐业务服务。"""

from __future__ import annotations

import json
from typing import Any, cast

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.play_count import PlayCount
from app.models.song import Song
from app.schemas.music import (
    HotRecommendationsResponse,
    PersonalizedRecommendationsResponse,
    RecommendationStrategy,
    TrackResponse,
)


class RecommendationService:
    """推荐读取与降级服务。"""

    _TWO_TOWER_KEY_VERSION = 2
    _CONTENT_KEY_VERSION = 1

    @classmethod
    def _build_two_tower_key(cls, user_id: int) -> str:
        """主策略 key：双塔结果。"""
        return f"rec:user:{user_id}:v{cls._TWO_TOWER_KEY_VERSION}"

    @classmethod
    def _build_content_fallback_key(cls, user_id: int) -> str:
        """冷启动策略 key：内容推荐结果。"""
        return f"rec:user:{user_id}:v{cls._CONTENT_KEY_VERSION}"

    @classmethod
    def _build_legacy_content_fallback_key(cls, user_id: int) -> str:
        """兼容早期实现的内容推荐 key。"""
        return f"rec:user:{user_id}:content:v{cls._CONTENT_KEY_VERSION}"

    def __init__(self, db: AsyncSession, redis_client: Redis):
        self.db = db
        self.redis_client = redis_client

    @staticmethod
    def _to_track_response(
        *,
        song_pk: int,
        song_id: str,
        name: str | None,
        artist_name: str | None,
        song_length: int | None,
    ) -> TrackResponse:
        """将歌曲基础字段转换为前端 Track 结构。"""
        return TrackResponse(
            id=song_pk,
            song_id=song_id,
            name=name or song_id,
            artist=artist_name or "未知艺术家",
            album="未知专辑",
            cover_url="",
            duration_ms=song_length or 0,
        )

    async def _load_tracks_by_song_pk_ids(
        self, song_pk_ids: list[int]
    ) -> list[TrackResponse]:
        """按歌曲主键批量查询并保持输入顺序。"""
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
                self._to_track_response(
                    song_pk=int(row.id),
                    song_id=str(row.song_id),
                    name=row.name,
                    artist_name=row.artist_name,
                    song_length=row.song_length,
                )
            )
        return tracks

    async def get_hot_recommendations(
        self,
        *,
        limit: int,
        offset: int,
    ) -> HotRecommendationsResponse:
        """读取全局热门推荐，优先命中 Redis 缓存。"""
        cache_key = f"rec:global:hot:v1:{limit}:{offset}"
        cached: str | None = None
        try:
            cached = await self.redis_client.get(cache_key)
        except Exception:
            cached = None
        if cached:
            return HotRecommendationsResponse.model_validate_json(cached)

        total_stmt = select(func.count(PlayCount.id))
        total = int(await self.db.scalar(total_stmt) or 0)

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

        response = HotRecommendationsResponse(
            limit=limit,
            offset=offset,
            total=total,
            items=tracks,
        )

        try:
            await self.redis_client.setex(
                cache_key,
                settings.recommendation_hot_cache_ttl_seconds,
                response.model_dump_json(),
            )
        except Exception:
            # 缓存写入失败不应影响主流程，仍返回数据库结果。
            pass
        return response

    @staticmethod
    def _normalize_strategy(strategy: str | None) -> RecommendationStrategy:
        """规范化策略值，未知策略默认按 content_cold_start 处理。"""
        value = (strategy or "").strip()
        if value in {"two_tower", "content_cold_start", "global_hot"}:
            return cast(RecommendationStrategy, value)
        return "content_cold_start"

    @staticmethod
    def _extract_song_ids_from_payload(items: Any) -> list[str]:
        """从 Redis payload 中提取去重后的 song_id 列表，并保持原顺序。"""
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
        """按给定 key 读取推荐 payload。"""
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

    async def _build_personalized_response_from_payload(
        self,
        *,
        payload: dict[str, Any],
        strategy: RecommendationStrategy,
        limit: int,
        offset: int,
    ) -> PersonalizedRecommendationsResponse | None:
        """将 Redis payload 转为分页响应；若 payload 不可用则返回 None。"""
        all_song_ids = self._extract_song_ids_from_payload(payload.get("items"))
        total = len(all_song_ids)
        if total <= 0:
            return None

        page_song_ids = all_song_ids[offset : offset + limit]
        page_tracks = await self._load_tracks_by_song_ids(page_song_ids)

        # 命中缓存后，分页为空属于正常场景（例如 offset 超过总数）；
        # 若当前分页有 song_id 但全部无法映射到歌曲表，则视为无效 payload。
        if page_song_ids and not page_tracks:
            return None

        return PersonalizedRecommendationsResponse(
            strategy=strategy,
            limit=limit,
            offset=offset,
            total=total,
            items=page_tracks,
        )

    async def _load_tracks_by_song_ids(
        self, song_ids: list[str]
    ) -> list[TrackResponse]:
        """按 song_id 列表查询歌曲并转为 TrackResponse，保持输入顺序。"""
        if not song_ids:
            return []

        stmt = select(
            Song.id,
            Song.song_id,
            Song.name,
            Song.artist_name,
            Song.song_length,
        ).where(Song.song_id.in_(song_ids))
        rows = (await self.db.execute(stmt)).all()
        row_map = {str(row.song_id): row for row in rows}

        tracks: list[TrackResponse] = []
        for song_id in song_ids:
            row = row_map.get(song_id)
            if row is None:
                continue
            tracks.append(
                self._to_track_response(
                    song_pk=int(row.id),
                    song_id=str(row.song_id),
                    name=row.name,
                    artist_name=row.artist_name,
                    song_length=row.song_length,
                )
            )
        return tracks

    async def get_personalized_recommendations(
        self,
        *,
        user_id: int,
        limit: int,
        offset: int,
    ) -> PersonalizedRecommendationsResponse:
        """按 two_tower -> content_cold_start -> global_hot 顺序读取推荐。"""
        two_tower_key = self._build_two_tower_key(user_id)
        two_tower_payload = await self._get_payload_by_key(cache_key=two_tower_key)
        if two_tower_payload is not None:
            primary_strategy = self._normalize_strategy(
                str(two_tower_payload.get("strategy") or "")
            )

            if primary_strategy == "two_tower":
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

            # 兼容当前 P5：content_based 仍写在 rec:user:{id}:v1。
            if primary_strategy == "content_cold_start":
                content_response = await self._build_personalized_response_from_payload(
                    payload=two_tower_payload,
                    strategy="content_cold_start",
                    limit=limit,
                    offset=offset,
                )
                if content_response is not None:
                    return content_response

        for content_key in (
            self._build_content_fallback_key(user_id),
            self._build_legacy_content_fallback_key(user_id),
        ):
            content_payload = await self._get_payload_by_key(cache_key=content_key)
            if content_payload is None:
                continue

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
