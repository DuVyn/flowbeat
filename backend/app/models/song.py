"""歌曲模型。

字段语义参考：
- data/raw/songs.csv: song_id, song_length, artist_name, language
- data/raw/song_extra_info.csv: name
"""

from typing import List, Optional

from sqlalchemy import BigInteger, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.associations import song_composer_m2m, song_genre_m2m, song_lyricist_m2m
from app.models.music_meta import Composer, Genre, Lyricist


class Song(Base):
    """歌曲维度表，整合歌曲基础信息与扩展名称信息。"""

    __tablename__ = "songs"

    # 自增主键，供内部关系引用。
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    # 原始数据中的歌曲唯一标识（业务唯一键）。
    song_id: Mapped[str] = mapped_column(
        String(128), unique=True, index=True, nullable=False
    )
    # 歌曲名，通常来自 song_extra_info.csv 的 name。
    name: Mapped[Optional[str]] = mapped_column(String(255))
    # 艺术家名称。
    artist_name: Mapped[Optional[str]] = mapped_column(String(255))
    # 歌曲时长（毫秒）。
    song_length: Mapped[Optional[int]] = mapped_column(Integer)
    # 语言代码（如 3.0/31.0/52.0 等）。
    language: Mapped[Optional[float]] = mapped_column(Float)

    # 歌曲与流派的多对多关系（songs.genre_ids 拆分后的结果）。
    genres: Mapped[List["Genre"]] = relationship(
        secondary=song_genre_m2m, lazy="selectin"
    )
    # 歌曲与作曲家的多对多关系（songs.composer 拆分后的结果）。
    composers: Mapped[List["Composer"]] = relationship(
        secondary=song_composer_m2m, lazy="selectin"
    )
    # 歌曲与作词家的多对多关系（songs.lyricist 拆分后的结果）。
    lyricists: Mapped[List["Lyricist"]] = relationship(
        secondary=song_lyricist_m2m, lazy="selectin"
    )
