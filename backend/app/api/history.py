"""当前登录用户播放历史接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_auth_context
from app.db.session import get_db_session
from app.schemas.music import (
    PlayHistoryResponse,
    RecordPlayHistoryRequest,
    RecordPlayHistoryResponse,
)
from app.services.play_history_service import PlayHistoryService

router = APIRouter(prefix="/api/me", tags=["me"])


@router.post(
    "/history",
    response_model=RecordPlayHistoryResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_play_history(
    payload: RecordPlayHistoryRequest,
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> RecordPlayHistoryResponse:
    """记录当前用户一次播放。"""
    service = PlayHistoryService(db)
    return await service.record_play_history(
        user_id=auth_context.user.id, payload=payload
    )


@router.get("/history", response_model=PlayHistoryResponse)
async def get_play_history(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> PlayHistoryResponse:
    """分页获取当前用户最近播放历史。"""
    service = PlayHistoryService(db)
    return await service.get_play_history(
        user_id=auth_context.user.id,
        limit=limit,
        offset=offset,
    )
