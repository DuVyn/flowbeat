"""当前登录用户收藏接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_auth_context
from app.db.session import get_db_session
from app.schemas.music import FavoriteListResponse, FavoriteToggleResponse
from app.services.favorite_service import FavoriteService

router = APIRouter(prefix="/api/me/favorites", tags=["favorites"])


@router.post("/{song_id}/toggle", response_model=FavoriteToggleResponse)
async def toggle_favorite_song(
    song_id: int,
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> FavoriteToggleResponse:
    """切换当前用户对指定歌曲的收藏状态。"""

    service = FavoriteService(db)
    return await service.toggle_favorite(user_id=auth_context.user.id, song_id=song_id)


@router.get("", response_model=FavoriteListResponse)
async def get_favorite_songs(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> FavoriteListResponse:
    """分页读取当前用户收藏的歌曲列表。"""

    service = FavoriteService(db)
    return await service.get_favorite_list(
        user_id=auth_context.user.id,
        limit=limit,
        offset=offset,
    )
