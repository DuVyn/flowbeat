"""用户资料接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_auth_context
from app.db.session import get_db_session
from app.schemas.music import ListeningInsightsResponse
from app.schemas.user import UpdateUserProfileRequest, UserProfileResponse
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


@router.get("/insights/genres", response_model=ListeningInsightsResponse)
async def get_listening_genre_insights(
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> ListeningInsightsResponse:
    """获取当前用户高频收听的前五个流派及权重。"""

    service = UserService(db)
    return await service.get_listening_genre_insights(user_id=auth_context.user.id)
