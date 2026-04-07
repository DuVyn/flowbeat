"""认证模块请求与响应模型。"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.schemas.user import UserProfileResponse

GenderValue = Literal["male", "female", "unknown"]
EmailString = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=6,
        max_length=255,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    ),
]


class RegisterRequest(BaseModel):
    """用户注册请求。"""

    model_config = ConfigDict(extra="forbid")

    username: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=255)
    ]
    gender: GenderValue
    birthday: date
    email: EmailString
    password: Annotated[str, StringConstraints(min_length=6, max_length=128)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class LoginRequest(BaseModel):
    """用户登录请求。"""

    model_config = ConfigDict(extra="forbid")

    email: EmailString
    password: Annotated[str, StringConstraints(min_length=1, max_length=128)]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()


class AuthResponse(BaseModel):
    """登录/注册响应。"""

    access_token: str
    refresh_token: str
    token_type: Literal["bearer"] = "bearer"
    access_expires_at: datetime
    refresh_expires_at: datetime
    user: UserProfileResponse


class LogoutResponse(BaseModel):
    """登出响应。"""

    detail: str = Field(default="登出成功")
