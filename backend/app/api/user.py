"""用户资料接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_auth_context
from app.db.session import get_db_session
from app.schemas.music import ListeningInsightsResponse
from app.schemas.user import (
    UpdateUserGenrePreferenceRequest,
    UpdateUserProfileRequest,
    UserGenrePreferenceResponse,
    UserProfileResponse,
)
from app.services.user_service import UserService, build_user_profile_response

router = APIRouter(prefix="/api/user", tags=["user"])


@router.get("/profile", response_model=UserProfileResponse)
async def get_profile(
    auth_context: AuthContext = Depends(get_auth_context),
) -> UserProfileResponse:
    """获取当前用户资料。"""
    return build_user_profile_response(auth_context.user)


@router.patch("/profile", response_model=UserProfileResponse)
async def update_profile(
    payload: UpdateUserProfileRequest,
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserProfileResponse:
    """按需更新用户资料。"""
    service = UserService(db)
    try:
        return await service.update_profile(user=auth_context.user, payload=payload)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.get("/preferences/genres", response_model=UserGenrePreferenceResponse)
async def get_preferred_genres(
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserGenrePreferenceResponse:
    """获取当前用户偏好流派编码列表。"""

    service = UserService(db)
    genre_codes = await service.get_preferred_genre_codes(user_id=auth_context.user.id)
    return UserGenrePreferenceResponse(genre_codes=genre_codes)


async def _update_preferred_genres(
    *,
    payload: UpdateUserGenrePreferenceRequest,
    auth_context: AuthContext,
    db: AsyncSession,
) -> UserGenrePreferenceResponse:
    """更新当前用户偏好流派（全量覆盖）。"""

    service = UserService(db)
    try:
        genre_codes = await service.update_preferred_genres(
            user=auth_context.user,
            genre_codes=payload.genre_codes,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    return UserGenrePreferenceResponse(genre_codes=genre_codes)


@router.put("/preferences/genres", response_model=UserGenrePreferenceResponse)
async def update_preferred_genres(
    payload: UpdateUserGenrePreferenceRequest,
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserGenrePreferenceResponse:
    return await _update_preferred_genres(
        payload=payload,
        auth_context=auth_context,
        db=db,
    )


@router.post("/preferences/genres", response_model=UserGenrePreferenceResponse)
async def update_preferred_genres_post(
    payload: UpdateUserGenrePreferenceRequest,
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> UserGenrePreferenceResponse:
    return await _update_preferred_genres(
        payload=payload,
        auth_context=auth_context,
        db=db,
    )


@router.get("/insights/genres", response_model=ListeningInsightsResponse)
async def get_listening_genre_insights(
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> ListeningInsightsResponse:
    """获取当前用户高频收听的前五个流派及权重。"""

    service = UserService(db)
    return await service.get_listening_genre_insights(user_id=auth_context.user.id)
