"""用户资料服务。"""

from __future__ import annotations

from sqlalchemy import delete, func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import SecurityError, calculate_age
from app.models.associations import song_genre_m2m, user_genre_preference_m2m
from app.models.play_history import PlayHistory
from app.models.song import Song
from app.models.song_meta import Genre
from app.models.user import GenderEnum, User
from app.schemas.music import GenrePreferenceItemResponse, ListeningInsightsResponse
from app.schemas.user import UpdateUserProfileRequest, UserProfileResponse
from app.services.genre_labels import format_genre_name


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

    async def get_listening_genre_insights(
        self, *, user_id: int
    ) -> ListeningInsightsResponse:
        """聚合当前用户高频收听的前五个流派。"""

        play_count_stmt = (
            select(
                Genre.genre_code,
                func.count(PlayHistory.id).label("play_count"),
            )
            .join(song_genre_m2m, song_genre_m2m.c.genre_id == Genre.id)
            .join(Song, Song.id == song_genre_m2m.c.song_id)
            .join(PlayHistory, PlayHistory.song_id == Song.id)
            .where(PlayHistory.user_id == user_id)
            .group_by(Genre.id, Genre.genre_code)
            .order_by(func.count(PlayHistory.id).desc(), Genre.genre_code.asc())
            .limit(5)
        )

        rows = (await self.db.execute(play_count_stmt)).all()
        total_plays = sum(int(row.play_count) for row in rows)

        if total_plays <= 0:
            preferred_stmt = (
                select(Genre.genre_code)
                .select_from(User)
                .join(User.preferred_genres)
                .where(User.id == user_id)
                .order_by(Genre.genre_code.asc())
                .limit(5)
            )
            preferred_rows = (await self.db.execute(preferred_stmt)).all()
            items = [
                GenrePreferenceItemResponse(
                    genre_code=str(row.genre_code),
                    genre_name=format_genre_name(str(row.genre_code)),
                    play_count=1,
                    weight=20.0,
                )
                for row in preferred_rows
            ]
            return ListeningInsightsResponse(
                total_plays=0,
                total_distinct_genres=len(items),
                items=items,
            )

        items = [
            GenrePreferenceItemResponse(
                genre_code=str(row.genre_code),
                genre_name=format_genre_name(str(row.genre_code)),
                play_count=int(row.play_count),
                weight=round((int(row.play_count) / total_plays) * 100, 2),
            )
            for row in rows
        ]

        return ListeningInsightsResponse(
            total_plays=total_plays,
            total_distinct_genres=len(items),
            items=items,
        )

    async def update_profile(
        self,
        *,
        user: User,
        payload: UpdateUserProfileRequest,
    ) -> UserProfileResponse:
        """按需更新用户名、性别与生日（映射为年龄）。"""
        has_changes = False

        if payload.username is not None:
            normalized_username = payload.username.strip()
            if not normalized_username:
                raise ValueError("用户名不能为空")
            user.nickname = normalized_username
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

    async def get_preferred_genre_codes(self, *, user_id: int) -> list[str]:
        """获取用户偏好流派编码列表。"""

        stmt = (
            select(Genre.genre_code)
            .select_from(user_genre_preference_m2m)
            .join(Genre, Genre.id == user_genre_preference_m2m.c.genre_id)
            .where(user_genre_preference_m2m.c.user_id == user_id)
            .order_by(Genre.genre_code.asc())
        )
        rows = (await self.db.execute(stmt)).scalars().all()
        return [str(row) for row in rows]

    async def update_preferred_genres(
        self,
        *,
        user: User,
        genre_codes: list[str],
    ) -> list[str]:
        """更新用户偏好流派（全量覆盖）。"""

        normalized_codes: list[str] = []
        seen_codes: set[str] = set()
        # 归一化并去重，避免重复或空白编码影响写入。
        for raw_code in genre_codes:
            code = raw_code.strip()
            if not code or code in seen_codes:
                continue
            seen_codes.add(code)
            normalized_codes.append(code)

        if not normalized_codes:
            raise ValueError("至少选择 1 个流派")

        stmt = select(Genre.id, Genre.genre_code).where(
            Genre.genre_code.in_(normalized_codes)
        )
        rows = (await self.db.execute(stmt)).all()
        found_codes = {str(row.genre_code) for row in rows}
        missing_codes = [code for code in normalized_codes if code not in found_codes]
        if missing_codes:
            raise ValueError(f"以下流派编码不存在：{', '.join(missing_codes)}")

        desired_ids = {int(row.id) for row in rows}
        existing_stmt = select(user_genre_preference_m2m.c.genre_id).where(
            user_genre_preference_m2m.c.user_id == user.id
        )
        existing_ids = {
            int(row) for row in (await self.db.execute(existing_stmt)).scalars().all()
        }

        ids_to_delete = existing_ids - desired_ids
        ids_to_insert = desired_ids - existing_ids

        if ids_to_delete:
            await self.db.execute(
                delete(user_genre_preference_m2m).where(
                    user_genre_preference_m2m.c.user_id == user.id,
                    user_genre_preference_m2m.c.genre_id.in_(ids_to_delete),
                )
            )

        if ids_to_insert:
            insert_payload = [
                {"user_id": user.id, "genre_id": genre_id} for genre_id in ids_to_insert
            ]
            await self.db.execute(insert(user_genre_preference_m2m), insert_payload)

        await self.db.commit()
        return normalized_codes
