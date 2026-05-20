"""用户资料请求与响应模型。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

GenderValue = Literal["male", "female", "unknown"]
NonEmptyUsername = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=255),
]
GenreCode = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=32),
]


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

    username: NonEmptyUsername | None = None
    gender: GenderValue | None = None
    birthday: date | None = None


class UpdateUserGenrePreferenceRequest(BaseModel):
    """更新用户偏好流派请求。"""

    model_config = ConfigDict(extra="forbid")

    genre_codes: list[GenreCode] = Field(min_length=1)


class UserGenrePreferenceResponse(BaseModel):
    """用户偏好流派响应。"""

    genre_codes: list[str]
