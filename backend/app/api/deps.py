"""API 层公共依赖。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecurityError, decode_auth_token
from app.db.session import get_db_session
from app.models.user import User
from app.models.user_session import UserSession

bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(slots=True)
class AuthContext:
    """当前请求的认证上下文。"""

    user: User
    session: UserSession


async def get_auth_context(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db_session),
) -> AuthContext:
    """解析 access token 并校验会话有效性。"""
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供有效的访问令牌",
        )

    try:
        token_payload = decode_auth_token(
            credentials.credentials,
            expected_token_type="access",
        )
    except SecurityError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc

    session_stmt = select(UserSession).where(
        UserSession.id == token_payload.session_id,
        UserSession.user_id == token_payload.user_id,
    )
    user_session = await db.scalar(session_stmt)
    now = datetime.now(timezone.utc)
    access_expires_at = user_session.access_expires_at if user_session else None
    if access_expires_at and access_expires_at.tzinfo is None:
        access_expires_at = access_expires_at.replace(tzinfo=timezone.utc)
    if (
        user_session is None
        or user_session.revoked_at is not None
        or access_expires_at is None
        or access_expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="会话已失效，请重新登录",
        )

    user = await db.get(User, token_payload.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在或已被删除",
        )

    return AuthContext(user=user, session=user_session)
