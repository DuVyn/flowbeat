"""推荐相关接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_auth_context
from app.core.cache import get_redis_client
from app.db.session import get_db_session
from app.schemas.music import (
    HotRecommendationsResponse,
    PersonalizedRecommendationsResponse,
)
from app.services.recommendation_service import RecommendationService

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])


@router.get("/hot", response_model=HotRecommendationsResponse)
async def get_hot_recommendations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
    redis_client: Redis = Depends(get_redis_client),
) -> HotRecommendationsResponse:
    """获取首页全局热门推荐。"""
    service = RecommendationService(
        db,
        redis_client,
        user_id=auth_context.user.id,
    )
    return await service.get_hot_recommendations(limit=limit, offset=offset)


@router.get("/personalized", response_model=PersonalizedRecommendationsResponse)
async def get_personalized_recommendations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
    redis_client: Redis = Depends(get_redis_client),
) -> PersonalizedRecommendationsResponse:
    """获取当前登录用户个性化推荐。"""
    service = RecommendationService(db, redis_client, user_id=auth_context.user.id)
    return await service.get_personalized_recommendations(
        user_id=auth_context.user.id,
        limit=limit,
        offset=offset,
    )


@router.get("/content", response_model=PersonalizedRecommendationsResponse)
async def get_content_recommendations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
    redis_client: Redis = Depends(get_redis_client),
) -> PersonalizedRecommendationsResponse:
    """获取当前用户的内容冷启动推荐。"""

    service = RecommendationService(db, redis_client, user_id=auth_context.user.id)
    return await service.get_content_recommendations(
        user_id=auth_context.user.id,
        limit=limit,
        offset=offset,
    )
