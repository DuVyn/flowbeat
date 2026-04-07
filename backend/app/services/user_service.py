"""用户资料服务。"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecurityError, calculate_age
from app.models.user import GenderEnum, User
from app.schemas.user import UpdateUserProfileRequest, UserProfileResponse


def build_user_profile_response(user: User) -> UserProfileResponse:
    """将 ORM 用户对象转换为 profile 响应。"""
    gender = user.gender.value if user.gender else "unknown"
    return UserProfileResponse(
        id=user.id,
        username=user.nickname,
        gender=gender,
        age=user.bd,
        email=user.email,
        registration_init_time=user.registration_init_time,
    )


class UserService:
    """用户资料相关业务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def update_profile(
        self,
        *,
        user: User,
        payload: UpdateUserProfileRequest,
    ) -> UserProfileResponse:
        """按需更新用户名、性别与生日（映射为年龄）。"""
        has_changes = False

        if payload.username is not None:
            user.nickname = payload.username.strip()
            has_changes = True

        if payload.gender is not None:
            user.gender = GenderEnum(payload.gender)
            has_changes = True

        if payload.birthday is not None:
            try:
                user.bd = calculate_age(payload.birthday)
            except SecurityError as exc:
                raise ValueError(str(exc)) from exc
            has_changes = True

        if not has_changes:
            return build_user_profile_response(user)

        await self.db.commit()
        await self.db.refresh(user)
        return build_user_profile_response(user)
