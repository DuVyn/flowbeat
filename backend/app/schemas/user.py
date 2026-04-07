"""用户资料请求与响应模型。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GenderValue = Literal["male", "female", "unknown"]


class UserProfileResponse(BaseModel):
    """个人中心展示模型。"""

    id: int
    username: str
    gender: GenderValue
    age: int | None
    email: str
    registration_init_time: datetime | None


class UpdateUserProfileRequest(BaseModel):
    """个人资料更新请求。"""

    model_config = ConfigDict(extra="forbid")

    username: str | None = Field(default=None, min_length=1, max_length=255)
    gender: GenderValue | None = None
    birthday: date | None = None
