"""缓存客户端依赖。"""

from fastapi import Request
from redis.asyncio import Redis

from app.core.config import settings


def create_redis_client() -> Redis:
    """创建 Redis 客户端实例。"""
    return Redis.from_url(
        settings.redis_uri,
        encoding="utf-8",
        decode_responses=True,
    )


def get_redis_client(request: Request) -> Redis:
    """FastAPI 依赖：从应用状态中获取 Redis 客户端。"""
    return request.app.state.redis_client
