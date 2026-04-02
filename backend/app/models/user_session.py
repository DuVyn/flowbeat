"""用户会话模型。

用于承载 JWT 鉴权会话信息：
- Access Token 有效期：2 小时
- Refresh Token 有效期：30 天
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class UserSession(Base):
    """用户会话表，支持多端登录与会话失效控制。"""

    __tablename__ = "user_sessions"

    # JWT 生命周期常量，供鉴权服务层直接复用。
    ACCESS_TOKEN_EXPIRES_IN = timedelta(hours=2)
    REFRESH_TOKEN_EXPIRES_IN = timedelta(days=30)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    # 仅保存 refresh token 哈希，避免明文 token 泄露风险。
    refresh_token_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    access_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    refresh_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    # 撤销时间不为空表示会话已失效（例如主动登出）。
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user = relationship("User", back_populates="sessions", lazy="selectin")

    @classmethod
    def build_access_expires_at(cls, now: Optional[datetime] = None) -> datetime:
        """计算 access token 过期时间（默认 2 小时，UTC 时区）。"""
        base_time = now or datetime.now(timezone.utc)
        return base_time + cls.ACCESS_TOKEN_EXPIRES_IN

    @classmethod
    def build_refresh_expires_at(cls, now: Optional[datetime] = None) -> datetime:
        """计算 refresh token 过期时间（默认 30 天，UTC 时区）。"""
        base_time = now or datetime.now(timezone.utc)
        return base_time + cls.REFRESH_TOKEN_EXPIRES_IN
