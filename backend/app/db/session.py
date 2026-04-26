"""数据库 Engine 与 Session 依赖。"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

engine = create_async_engine(
    settings.sqlalchemy_database_uri,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=1800,
    pool_timeout=30,
)

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI 依赖：按请求提供数据库会话。"""
    async with SessionLocal() as session:
        try:
            yield session
        except BaseException:
            # 请求被取消（例如开发期 Ctrl+C）时也要回滚，避免连接留有未完成事务。
            await session.rollback()
            raise


async def dispose_engine() -> None:
    """应用关闭时释放连接池资源。"""
    await engine.dispose()
