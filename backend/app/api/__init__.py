"""API Router 聚合。"""

from fastapi import APIRouter

from app.api.auth import router as auth_router
from app.api.history import router as history_router
from app.api.recommendations import router as recommendations_router
from app.api.songs import router as songs_router
from app.api.user import router as user_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(user_router)
api_router.include_router(history_router)
api_router.include_router(songs_router)
api_router.include_router(recommendations_router)

__all__ = ["api_router"]
