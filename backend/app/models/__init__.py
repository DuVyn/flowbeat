"""ORM 模型聚合导出，便于统一导入。"""

from app.models.associations import (
    song_composer_m2m,
    song_genre_m2m,
    song_lyricist_m2m,
    user_genre_preference_m2m,
)
from app.models.play_count import PlayCount
from app.models.play_history import PlayHistory
from app.models.song import Song
from app.models.song_meta import Composer, Genre, Lyricist
from app.models.user import User
from app.models.user_session import UserSession

# 显式声明对外暴露的模块
__all__ = [
    "Genre",
    "Composer",
    "Lyricist",
    "Song",
    "PlayCount",
    "PlayHistory",
    "User",
    "UserSession",
    "song_genre_m2m",
    "song_composer_m2m",
    "song_lyricist_m2m",
    "user_genre_preference_m2m",
]
