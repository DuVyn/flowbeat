"""认证业务服务。"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    SecurityError,
    calculate_age,
    create_auth_token,
    generate_msno,
    hash_password,
    hash_token,
    verify_password,
)
from app.models.user import GenderEnum, User
from app.models.user_session import UserSession
from app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest
from app.services.user_service import build_user_profile_response


class AuthService:
    """认证服务：注册、登录、登出。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def register(self, payload: RegisterRequest) -> AuthResponse:
        """注册用户并直接返回 token。"""
        exists_stmt = select(User.id).where(User.email == payload.email)
        exists_user_id = await self.db.scalar(exists_stmt)
        if exists_user_id is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="邮箱已注册",
            )

        now = datetime.now(timezone.utc)
        try:
            age = calculate_age(payload.birthday)
        except SecurityError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=str(exc),
            ) from exc

        user = User(
            msno=generate_msno(),
            nickname=payload.username.strip(),
            email=payload.email,
            password=hash_password(payload.password),
            bd=age,
            gender=GenderEnum(payload.gender),
            registration_init_time=now,
        )
        self.db.add(user)
        await self.db.flush()

        auth_response = await self._issue_token_bundle(user=user, now=now)
        await self.db.commit()
        await self.db.refresh(user)
        return auth_response

    async def login(self, payload: LoginRequest) -> AuthResponse:
        """用户登录。"""
        stmt = select(User).where(User.email == payload.email)
        user = await self.db.scalar(stmt)
        if user is None or not verify_password(payload.password, user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="邮箱或密码错误",
            )

        auth_response = await self._issue_token_bundle(
            user=user,
            now=datetime.now(timezone.utc),
        )
        await self.db.commit()
        return auth_response

    async def logout(self, current_session: UserSession) -> None:
        """登出并清理当前会话。"""
        await self.db.delete(current_session)
        await self.db.commit()

    async def _issue_token_bundle(self, *, user: User, now: datetime) -> AuthResponse:
        """创建用户会话并签发 access/refresh token。"""
        access_expires_at = UserSession.build_access_expires_at(now)
        refresh_expires_at = UserSession.build_refresh_expires_at(now)

        session = UserSession(
            user_id=user.id,
            refresh_token_hash="pending",
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
        )
        self.db.add(session)
        await self.db.flush()

        access_token = create_auth_token(
            user_id=user.id,
            session_id=session.id,
            token_type="access",
            expires_at=access_expires_at,
        )
        refresh_token = create_auth_token(
            user_id=user.id,
            session_id=session.id,
            token_type="refresh",
            expires_at=refresh_expires_at,
        )
        session.refresh_token_hash = hash_token(refresh_token)

        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            access_expires_at=access_expires_at,
            refresh_expires_at=refresh_expires_at,
            user=build_user_profile_response(user),
        )
