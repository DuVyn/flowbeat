"""用户模型。

字段语义参考 data/raw/members.csv：
- msno: 用户唯一标识
- city: 城市编码
- bd: 年龄（0 常表示未知）
- gender: 性别
"""

import enum
from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.play_history import PlayHistory
    from app.models.user_session import UserSession


class GenderEnum(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    UNKNOWN = "unknown"


class User(Base):
    """用户维度表，对应 members.csv 的核心字段。"""

    __tablename__ = "users"

    # 自增主键，供内部关系引用。
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 加密用户标识（业务唯一键）。
    msno: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    # 邮箱（唯一登录标识）。
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    # 哈希后的密码。
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    # 城市编码。
    city: Mapped[Optional[int]] = mapped_column(Integer)
    # 年龄；原始数据中 0 往往表示未知。
    bd: Mapped[Optional[int]] = mapped_column(Integer)
    # 性别；为空时通常表示未知。
    gender: Mapped[Optional[GenderEnum]] = mapped_column(nullable=True)
    # 注册时间
    registration_init_time: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    # 用户会话，一对多关系，用于支撑 JWT 刷新与失效控制。
    sessions: Mapped[List["UserSession"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
    # 用户播放历史，一对多关系，用于历史播放页面查询。
    play_histories: Mapped[List["PlayHistory"]] = relationship(
        back_populates="user", cascade="all, delete-orphan", lazy="selectin"
    )
