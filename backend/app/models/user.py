"""用户模型。

字段语义参考 data/raw/members.csv：
- msno: 用户唯一标识
- city: 城市编码
- bd: 年龄（0 常表示未知）
- gender: 性别
"""

from typing import List, Optional

from sqlalchemy import BigInteger, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import user_genre_preference_m2m
from app.models.music_meta import Genre


class User(Base):
    """用户维度表，对应 members.csv 的核心字段。"""

    __tablename__ = "users"

    # 自增主键，供内部关系引用。
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 加密用户标识（业务唯一键）。
    msno: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    # 城市编码。
    city: Mapped[Optional[int]] = mapped_column(Integer)
    # 年龄；原始数据中 0 往往表示未知。
    bd: Mapped[Optional[int]] = mapped_column(Integer)
    # 性别；为空时通常表示未知。
    gender: Mapped[Optional[str]] = mapped_column(String(16))

    # 用户偏好流派，多对多关联到 Genre。
    preferred_genres: Mapped[List["Genre"]] = relationship(
        secondary=user_genre_preference_m2m, lazy="selectin"
    )
