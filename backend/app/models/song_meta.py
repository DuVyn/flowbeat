"""歌曲元数据维表。

用于承接 songs.csv 中可拆分的多值字段：
- genre_ids -> Genre
- composer -> Composer
- lyricist -> Lyricist
"""

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Genre(Base):
    """流派维表。"""

    __tablename__ = "genres"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 对应 songs.csv 中的单个 genre_id 编码。
    genre_code: Mapped[str] = mapped_column(
        String(32), unique=True, index=True, nullable=False
    )


class Composer(Base):
    """作曲家维表。"""

    __tablename__ = "composers"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 作曲家名称（由 songs.csv 的 composer 拆分去重）。
    name: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )


class Lyricist(Base):
    """作词家维表。"""

    __tablename__ = "lyricists"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 作词家名称（由 songs.csv 的 lyricist 拆分去重）。
    name: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
