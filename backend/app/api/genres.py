"""流派目录接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_auth_context
from app.db.session import get_db_session
from app.schemas.music import GenreCatalogResponse, SongFeedResponse
from app.services.genre_service import GenreService

router = APIRouter(prefix="/api/genres", tags=["genres"])


@router.get("", response_model=GenreCatalogResponse)
async def get_genre_catalog(
    db: AsyncSession = Depends(get_db_session),
) -> GenreCatalogResponse:
    """获取全部流派目录。"""

    service = GenreService(db)
    return await service.get_genre_catalog()


@router.get("/{genre_code}/songs", response_model=SongFeedResponse)
async def get_genre_songs(
    genre_code: str,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SongFeedResponse:
    """按流派编码读取歌曲列表。"""

    service = GenreService(db, user_id=auth_context.user.id)
    return await service.get_genre_songs(
        genre_code=genre_code,
        limit=limit,
        offset=offset,
    )
