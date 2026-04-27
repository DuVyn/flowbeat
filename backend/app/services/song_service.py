"""歌曲播放相关业务服务。"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import re
from datetime import timedelta
from pathlib import PurePosixPath
from typing import Any

from fastapi import HTTPException, status
from fastapi.concurrency import run_in_threadpool
from minio import Minio
from minio.error import S3Error
from pydantic import ValidationError
from redis.asyncio import Redis
from sqlalchemy import or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.song import Song
from app.schemas.music import (
    SongCoversResponse,
    SongDetailResponse,
    SongFeedResponse,
    SongSearchResponse,
    SongStreamResponse,
    TrackResponse,
)
from app.services.track_mapper import to_track_response

logger = logging.getLogger(__name__)


def build_track_response(
    *,
    song_pk: int,
    song_id: str,
    name: str | None,
    artist_name: str | None,
    song_length: int | None,
) -> TrackResponse:
    """兼容旧调用入口，实际映射委托给共享 mapper。"""
    return to_track_response(
        song_pk=song_pk,
        song_id=song_id,
        name=name,
        artist_name=artist_name,
        song_length=song_length,
    )


# 限制同时在线的 presign threadpool 任务数量，
# 避免 100 个并发 presign 调用堵死默认 40 线程的 AnyIO threadpool。
_PRESIGN_SEMAPHORE = asyncio.Semaphore(8)


class SongService:
    """歌曲查询与可播放地址签发服务。"""

    _SEARCH_CACHE_KEY_VERSION = 1
    _SEARCH_CACHE_TTL_SECONDS = 300
    _SEARCH_TOKEN_PATTERN = re.compile(r"[0-9A-Za-z\u4e00-\u9fff]+")
    _COVER_CACHE_TTL_SECONDS = 1800  # 封面 presign URL 缓存 30 分钟

    @classmethod
    def _build_search_cache_key(
        cls,
        *,
        query: str,
        limit: int,
        offset: int,
    ) -> str:
        normalized = " ".join(query.strip().lower().split())
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()
        return (
            f"search:songs:v{cls._SEARCH_CACHE_KEY_VERSION}:{digest}:{limit}:{offset}"
        )

    @classmethod
    def _build_boolean_query(cls, query: str) -> str:
        """将自然语言关键词转换为 MySQL BOOLEAN MODE 查询串。"""
        tokens = cls._SEARCH_TOKEN_PATTERN.findall(query)
        if not tokens:
            return ""

        boolean_tokens: list[str] = []
        for token in tokens[:8]:
            cleaned = token.strip()
            if not cleaned:
                continue
            if len(cleaned) == 1:
                boolean_tokens.append(f"+{cleaned}")
            else:
                boolean_tokens.append(f"+{cleaned}*")
        return " ".join(boolean_tokens)

    async def _search_with_fulltext(
        self,
        *,
        query: str,
        limit: int,
        offset: int,
    ) -> list[Any]:
        """使用 FULLTEXT 索引执行搜索。"""
        boolean_query = self._build_boolean_query(query)
        if not boolean_query:
            return []

        fulltext_stmt = text(
            """
            SELECT
                id,
                song_id,
                name,
                artist_name,
                song_length
            FROM songs
            WHERE MATCH(name, artist_name, song_id)
                AGAINST (:q IN BOOLEAN MODE)
            LIMIT :limit_plus_one OFFSET :offset
            """
        )

        rows = (
            await self.db.execute(
                fulltext_stmt,
                {
                    "q": boolean_query,
                    "limit_plus_one": limit + 1,
                    "offset": offset,
                },
            )
        ).all()
        return list(rows)

    async def _search_with_prefix_fallback(
        self,
        *,
        query: str,
        limit: int,
        offset: int,
    ) -> list[Any]:
        """当 FULLTEXT 不可用时，退化为前缀匹配。"""
        prefix_keyword = f"{query}%"
        fallback_stmt = (
            select(
                Song.id,
                Song.song_id,
                Song.name,
                Song.artist_name,
                Song.song_length,
            )
            .where(
                or_(
                    Song.song_id.ilike(prefix_keyword),
                    Song.name.ilike(prefix_keyword),
                    Song.artist_name.ilike(prefix_keyword),
                )
            )
            .order_by(Song.id.asc())
            .limit(limit + 1)
            .offset(offset)
        )
        return list((await self.db.execute(fallback_stmt)).all())

    def __init__(
        self,
        db: AsyncSession,
        *,
        minio_client: Minio | None = None,
        redis_client: Redis | None = None,
    ):
        self.db = db
        self.minio_client = minio_client
        self.redis_client = redis_client

    @staticmethod
    def _build_cover_object_key(audio_object_key: str) -> str:
        """按音频对象键推导同编号封面对象键。"""
        file_name = PurePosixPath(audio_object_key).name
        track_stem = PurePosixPath(file_name).stem

        cover_prefix = settings.minio_cover_prefix.strip("/")
        cover_extension = settings.minio_cover_extension.strip().lstrip(".") or "svg"
        cover_file_name = f"{track_stem}.{cover_extension}"

        if cover_prefix:
            return str(PurePosixPath(cover_prefix) / cover_file_name)
        return cover_file_name

    async def search_songs(
        self,
        *,
        query: str,
        limit: int,
        offset: int,
    ) -> SongSearchResponse:
        """按关键词搜索歌曲（歌曲名 / 歌手 / song_id）。"""
        normalized_query = query.strip()
        if not normalized_query:
            return SongSearchResponse(
                query=normalized_query,
                limit=limit,
                offset=offset,
                has_more=False,
                items=[],
            )

        cache_key = self._build_search_cache_key(
            query=normalized_query,
            limit=limit,
            offset=offset,
        )

        if self.redis_client is not None:
            try:
                cached_payload: str | None = await self.redis_client.get(cache_key)
            except Exception:
                cached_payload = None

            if cached_payload:
                try:
                    return SongSearchResponse.model_validate_json(cached_payload)
                except ValidationError:
                    try:
                        await self.redis_client.delete(cache_key)
                    except Exception:
                        pass

        try:
            rows = await self._search_with_fulltext(
                query=normalized_query,
                limit=limit,
                offset=offset,
            )
        except Exception:
            rows = []

        if not rows:
            rows = await self._search_with_prefix_fallback(
                query=normalized_query,
                limit=limit,
                offset=offset,
            )

        has_more = len(rows) > limit
        page_rows = rows[:limit]
        items = [
            build_track_response(
                song_pk=int(row.id),
                song_id=str(row.song_id),
                name=row.name,
                artist_name=row.artist_name,
                song_length=row.song_length,
            )
            for row in page_rows
        ]

        response = SongSearchResponse(
            query=normalized_query,
            limit=limit,
            offset=offset,
            has_more=has_more,
            items=items,
        )

        if self.redis_client is not None:
            try:
                await self.redis_client.setex(
                    cache_key,
                    self._SEARCH_CACHE_TTL_SECONDS,
                    response.model_dump_json(),
                )
            except Exception:
                pass

        return response

    async def get_song_detail(self, song_id: int) -> SongDetailResponse:
        """根据歌曲主键获取详情。"""
        detail_stmt = select(
            Song.id,
            Song.song_id,
            Song.name,
            Song.artist_name,
            Song.song_length,
            Song.language,
            Song.audio_object_key,
        ).where(Song.id == song_id)
        row = (await self.db.execute(detail_stmt)).first()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="歌曲不存在",
            )

        base_track = build_track_response(
            song_pk=int(row.id),
            song_id=str(row.song_id),
            name=row.name,
            artist_name=row.artist_name,
            song_length=row.song_length,
        )
        return SongDetailResponse(
            **base_track.model_dump(),
            language=row.language,
            audio_object_key=row.audio_object_key,
        )

    async def get_song_stream(self, song_id: int) -> SongStreamResponse:
        """签发 MinIO 预签名播放地址。"""
        stream_stmt = select(Song.id, Song.audio_object_key).where(Song.id == song_id)
        row = (await self.db.execute(stream_stmt)).first()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="歌曲不存在",
            )
        if not row.audio_object_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该歌曲暂无可播放音频",
            )
        if self.minio_client is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="音频服务未初始化",
            )

        try:
            stream_url = await run_in_threadpool(
                self.minio_client.presigned_get_object,
                settings.minio_song_bucket,
                row.audio_object_key,
                expires=timedelta(seconds=settings.minio_presign_expires_seconds),
            )
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject"}:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="音频对象不存在：数据库对象键与 MinIO 对象名不一致",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="音频服务暂不可用，请稍后重试",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="音频服务网络异常，请稍后重试",
            ) from exc

        return SongStreamResponse(
            song_id=int(row.id),
            stream_url=stream_url,
            expires_in_seconds=settings.minio_presign_expires_seconds,
        )

    async def get_song_cover(self, song_id: int) -> str:
        """签发 MinIO 预签名封面地址。"""
        cover_stmt = select(Song.id, Song.audio_object_key).where(Song.id == song_id)
        row = (await self.db.execute(cover_stmt)).first()

        if row is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="歌曲不存在",
            )
        if not row.audio_object_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="该歌曲暂无可展示封面",
            )
        if self.minio_client is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="封面服务未初始化",
            )

        cover_object_key = self._build_cover_object_key(str(row.audio_object_key))

        try:
            return await run_in_threadpool(
                self.minio_client.presigned_get_object,
                settings.minio_song_bucket,
                cover_object_key,
                expires=timedelta(seconds=settings.minio_presign_expires_seconds),
            )
        except S3Error as exc:
            if exc.code in {"NoSuchKey", "NoSuchObject"}:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="封面对象不存在：请检查 MinIO 中封面键是否与音频编号一致",
                ) from exc
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="封面服务暂不可用，请稍后重试",
            ) from exc
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="封面服务网络异常，请稍后重试",
            ) from exc

    @classmethod
    def _build_cover_cache_key(cls, song_pk: int) -> str:
        """封面 presign URL 缓存 key。"""
        return f"cover:presign:{song_pk}"

    async def get_song_covers_batch(self, song_ids: list[int]) -> SongCoversResponse:
        """批量签发 MinIO 预签名封面地址。

        优先从 Redis 读取缓存，未命中的 ID 再通过 DB + MinIO presign 解析。
        使用信号量限制并发 presign 数量，避免 threadpool 饱和。
        """
        minio_client = self.minio_client
        if not song_ids or minio_client is None:
            return SongCoversResponse(covers={})

        unique_ids = list(dict.fromkeys(song_ids))[:100]
        covers: dict[int, str] = {}

        # ---- 阶段 1：从 Redis 批量读取已缓存的 presign URL ----
        ids_to_presign: list[int] = []
        if self.redis_client is not None:
            try:
                cache_keys = [self._build_cover_cache_key(sid) for sid in unique_ids]
                cached_values = await self.redis_client.mget(cache_keys)
                for sid, cached in zip(unique_ids, cached_values):
                    if cached:
                        covers[sid] = cached
                    else:
                        ids_to_presign.append(sid)
            except Exception:
                ids_to_presign = list(unique_ids)
        else:
            ids_to_presign = list(unique_ids)

        if not ids_to_presign:
            return SongCoversResponse(covers=covers)

        # ---- 阶段 2：查询需要 presign 的行 ----
        cover_stmt = select(Song.id, Song.audio_object_key).where(
            Song.id.in_(ids_to_presign)
        )
        rows = (await self.db.execute(cover_stmt)).all()

        # ---- 阶段 3：受信号量保护的并发 presign ----
        async def presign_one(
            song_pk: int, audio_object_key: str
        ) -> tuple[int, str] | None:
            cover_object_key = self._build_cover_object_key(audio_object_key)
            async with _PRESIGN_SEMAPHORE:
                try:
                    url = await run_in_threadpool(
                        minio_client.presigned_get_object,
                        settings.minio_song_bucket,
                        cover_object_key,
                        expires=timedelta(
                            seconds=settings.minio_presign_expires_seconds
                        ),
                    )
                    return (song_pk, url)
                except Exception:
                    return None

        tasks = [
            presign_one(int(row.id), str(row.audio_object_key))
            for row in rows
            if row.audio_object_key
        ]
        results = await asyncio.gather(*tasks)

        # ---- 阶段 4：写入缓存 & 汇总结果 ----
        cache_pipeline_items: list[tuple[str, str]] = []
        for result in results:
            if result is not None:
                covers[result[0]] = result[1]
                cache_pipeline_items.append(
                    (self._build_cover_cache_key(result[0]), result[1])
                )

        if cache_pipeline_items and self.redis_client is not None:
            try:
                pipe = self.redis_client.pipeline()
                for key, url in cache_pipeline_items:
                    pipe.setex(key, self._COVER_CACHE_TTL_SECONDS, url)
                await pipe.execute()
            except Exception:
                pass

        return SongCoversResponse(covers=covers)

    async def get_latest_songs(self, *, limit: int, offset: int) -> SongFeedResponse:
        """按主键倒序返回最近入库的歌曲。"""

        query_limit = limit + 1
        stmt = (
            select(
                Song.id,
                Song.song_id,
                Song.name,
                Song.artist_name,
                Song.song_length,
            )
            .order_by(Song.id.desc())
            .limit(query_limit)
            .offset(offset)
        )
        rows = (await self.db.execute(stmt)).all()
        has_more = len(rows) > limit
        page_rows = rows[:limit]
        items = [
            build_track_response(
                song_pk=int(row.id),
                song_id=str(row.song_id),
                name=row.name,
                artist_name=row.artist_name,
                song_length=row.song_length,
            )
            for row in page_rows
        ]
        return SongFeedResponse(
            title="新歌速递",
            limit=limit,
            offset=offset,
            has_more=has_more,
            items=items,
        )
