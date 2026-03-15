"""对象存储客户端依赖。"""

from fastapi import Request
from minio import Minio

from app.core.config import settings


def create_minio_client() -> Minio:
    """创建 MinIO 客户端实例。"""
    return Minio(
        endpoint=settings.minio_endpoint,
        access_key=settings.minio_root_user,
        secret_key=settings.minio_root_password,
        secure=settings.minio_secure,
    )


def get_minio_client(request: Request) -> Minio:
    """FastAPI 依赖：从应用状态中获取 MinIO 客户端。"""
    return request.app.state.minio_client
