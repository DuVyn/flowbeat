"""Content-Based 特征构建模块。

本模块提供两个可复用的数据构建能力：
1. P1：歌曲内容画像构建（song_content_profile）
2. P2：用户偏好画像构建（user_preference_profile）
"""

from .song_content_profile import (
    SongContentProfileBuildSummary,
    build_song_content_profile,
)
from .user_preference_profile import (
    UserPreferenceProfileBuildSummary,
    build_user_preference_profile,
)

__all__ = [
    "SongContentProfileBuildSummary",
    "UserPreferenceProfileBuildSummary",
    "build_song_content_profile",
    "build_user_preference_profile",
]
