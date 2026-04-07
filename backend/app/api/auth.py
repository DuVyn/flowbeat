"""认证接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_auth_context
from app.db.session import get_db_session
from app.schemas.auth import AuthResponse, LoginRequest, LogoutResponse, RegisterRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post(
    "/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    payload: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    """用户注册。"""
    service = AuthService(db)
    return await service.register(payload)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db_session),
) -> AuthResponse:
    """用户登录。"""
    service = AuthService(db)
    return await service.login(payload)


@router.post("/logout", response_model=LogoutResponse)
async def logout(
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> LogoutResponse:
    """用户登出。"""
    service = AuthService(db)
    await service.logout(auth_context.session)
    return LogoutResponse()
