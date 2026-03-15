"""ORM 模型聚合导出，便于统一导入。"""

from app.models.associations import (
    song_composer_m2m,
    song_genre_m2m,
    song_lyricist_m2m,
    user_genre_preference_m2m,
)
from app.models.music_meta import Composer, Genre, Lyricist
from app.models.song import Song
from app.models.user import User

# 显式声明对外暴露的模块
__all__ = [
    "Genre",
    "Composer",
    "Lyricist",
    "Song",
    "User",
    "song_genre_m2m",
    "song_composer_m2m",
    "song_lyricist_m2m",
    "user_genre_preference_m2m",
]
