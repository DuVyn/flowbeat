"""FastAPI 应用入口。"""

import asyncio
from contextlib import asynccontextmanager
from inspect import isawaitable

from fastapi import Depends, FastAPI, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import api_router
from app.core.cache import create_redis_client, get_redis_client
from app.core.config import settings
from app.core.storage import create_minio_client, get_minio_client
from app.db.session import dispose_engine, get_db_session


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：初始化并释放外部资源。"""
    app.state.minio_client = create_minio_client()
    app.state.redis_client = create_redis_client()
    try:
        yield
    finally:
        await app.state.redis_client.aclose()
        await dispose_engine()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def handle_cancelled_request(request: Request, call_next):
    """开发期 Ctrl+C 触发关闭时，避免取消请求输出整段异常栈。"""
    try:
        return await call_next(request)
    except asyncio.CancelledError:
        return JSONResponse(
            status_code=503,
            content={"detail": "服务正在关闭，请稍后重试"},
        )


app.include_router(api_router)


@app.get("/health", tags=["health"])
async def health_check(
    db: AsyncSession = Depends(get_db_session),
    minio_client=Depends(get_minio_client),
    redis_client: Redis = Depends(get_redis_client),
) -> JSONResponse:
    """最小健康检查：验证 MySQL、MinIO 与 Redis 连通性。"""
    mysql_ok = True
    minio_ok = True
    redis_ok = True
    mysql_error: str | None = None
    minio_error: str | None = None
    redis_error: str | None = None

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        mysql_ok = False
        mysql_error = str(exc)

    try:
        await run_in_threadpool(minio_client.list_buckets)
    except Exception as exc:
        minio_ok = False
        minio_error = str(exc)

    try:
        redis_ping_result = redis_client.ping()
        if isawaitable(redis_ping_result):
            redis_ping_result = await redis_ping_result
        redis_ok = bool(redis_ping_result)
    except Exception as exc:
        redis_ok = False
        redis_error = str(exc)

    overall_ok = mysql_ok and minio_ok and redis_ok
    status_code = 200 if overall_ok else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ok" if overall_ok else "degraded",
            "mysql": {"ok": mysql_ok, "error": mysql_error},
            "minio": {"ok": minio_ok, "error": minio_error},
            "redis": {"ok": redis_ok, "error": redis_error},
        },
    )
