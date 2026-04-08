"""Pydantic Schema 聚合导出。"""

from app.schemas.auth import AuthResponse, LoginRequest, LogoutResponse, RegisterRequest
from app.schemas.music import (
    HotRecommendationsResponse,
    SongDetailResponse,
    SongStreamResponse,
    TrackResponse,
)
from app.schemas.user import UpdateUserProfileRequest, UserProfileResponse

__all__ = [
    "RegisterRequest",
    "LoginRequest",
    "AuthResponse",
    "LogoutResponse",
    "TrackResponse",
    "SongDetailResponse",
    "SongStreamResponse",
    "HotRecommendationsResponse",
    "UserProfileResponse",
    "UpdateUserProfileRequest",
]
