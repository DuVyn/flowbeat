"""非个性化推荐业务服务。"""

from __future__ import annotations

from redis.asyncio import Redis
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.play_count import PlayCount
from app.models.song import Song
from app.schemas.music import HotRecommendationsResponse
from app.services.song_service import build_track_response


class RecommendationService:
    """首页全局推荐（热门）服务。"""

    def __init__(self, db: AsyncSession, redis_client: Redis):
        self.db = db
        self.redis_client = redis_client

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

        query_stmt = (
            select(Song)
            .join(PlayCount, PlayCount.song_id == Song.id)
            .order_by(PlayCount.total_play_count.desc())
            .limit(limit)
            .offset(offset)
        )
        songs = list((await self.db.scalars(query_stmt)).all())

        response = HotRecommendationsResponse(
            limit=limit,
            offset=offset,
            total=total,
            items=[build_track_response(song) for song in songs],
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
