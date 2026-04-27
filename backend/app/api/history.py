"""当前登录用户播放历史接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import AuthContext, get_auth_context
from app.db.session import get_db_session
from app.schemas.music import (
    ClearPlayHistoryResponse,
    PlayHistoryItemResponse,
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


@router.get("/history/latest", response_model=PlayHistoryItemResponse)
async def get_latest_play_history(
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> PlayHistoryItemResponse:
    """获取当前用户最近一次播放记录。"""

    service = PlayHistoryService(db)
    latest_item = await service.get_latest_play_history(user_id=auth_context.user.id)
    if latest_item is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="暂无播放历史"
        )
    return latest_item


@router.delete("/history", response_model=ClearPlayHistoryResponse)
async def clear_play_history(
    auth_context: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> ClearPlayHistoryResponse:
    """清空当前用户的播放历史。"""

    service = PlayHistoryService(db)
    return await service.clear_play_history(user_id=auth_context.user.id)
