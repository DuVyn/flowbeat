"""多对多关联表定义。

用于连接歌曲与元数据维表，支撑范式化后的关系建模。
"""

from sqlalchemy import BigInteger, Column, ForeignKey, Table

from app.db.base import Base

# 歌曲 <-> 流派
song_genre_m2m = Table(
    "song_genre_m2m",
    Base.metadata,
    Column(
        "song_id",
        BigInteger,
        ForeignKey("songs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "genre_id",
        BigInteger,
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# 用户 <-> 偏好流派
user_genre_preference_m2m = Table(
    "user_genre_preference_m2m",
    Base.metadata,
    Column(
        "user_id",
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "genre_id",
        BigInteger,
        ForeignKey("genres.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# 歌曲 <-> 作曲家
song_composer_m2m = Table(
    "song_composer_m2m",
    Base.metadata,
    Column(
        "song_id",
        BigInteger,
        ForeignKey("songs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "composer_id",
        BigInteger,
        ForeignKey("composers.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

# 歌曲 <-> 作词家
song_lyricist_m2m = Table(
    "song_lyricist_m2m",
    Base.metadata,
    Column(
        "song_id",
        BigInteger,
        ForeignKey("songs.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "lyricist_id",
        BigInteger,
        ForeignKey("lyricists.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
