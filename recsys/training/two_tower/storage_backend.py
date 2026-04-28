"""存储后端抽象：统一 Local 与 Cloud 文件系统接口。

根据 environment 配置自动选择底层实现：
- LocalBackend：标准本地文件系统操作
- CloudBackend：通过对象存储 SDK（如 COS / S3）进行读写
"""

from __future__ import annotations

import io
import json
import os
import shutil
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

import pandas as pd
import torch

from training.two_tower.config_schema import CloudConfig, PathsConfig


# ---------------------------------------------------------------------------
# 抽象基类
# ---------------------------------------------------------------------------

class StorageBackend(ABC):
    """文件 I/O 后端抽象。"""

    @abstractmethod
    def read_csv(self, path: str, **kwargs: Any) -> pd.DataFrame:
        """读取 CSV 并返回 DataFrame。"""

    @abstractmethod
    def save_checkpoint(self, state_dict: dict[str, Any], path: str) -> None:
        """保存 PyTorch checkpoint。"""

    @abstractmethod
    def load_checkpoint(self, path: str, map_location: str = "cpu") -> dict[str, Any]:
        """加载 PyTorch checkpoint。"""

    @abstractmethod
    def save_tensor(self, tensor: torch.Tensor, path: str) -> None:
        """保存单个 Tensor。"""

    @abstractmethod
    def save_json(self, payload: Any, path: str) -> None:
        """保存 JSON 文件。"""

    @abstractmethod
    def exists(self, path: str) -> bool:
        """检查路径是否存在。"""

    @abstractmethod
    def makedirs(self, path: str) -> None:
        """确保目录存在（含父级）。"""


# ---------------------------------------------------------------------------
# Local 实现
# ---------------------------------------------------------------------------

class LocalBackend(StorageBackend):
    """基于本地文件系统的存储后端。"""

    def __init__(self, workspace_root: Path) -> None:
        self.workspace_root = workspace_root.resolve()

    def _resolve(self, path_text: str) -> Path:
        p = Path(path_text).expanduser()
        if p.is_absolute():
            return p.resolve()
        return (self.workspace_root / p).resolve()

    def read_csv(self, path: str, **kwargs: Any) -> pd.DataFrame:
        resolved = self._resolve(path)
        if not resolved.exists():
            raise FileNotFoundError(f"CSV 文件不存在: {resolved}")
        return pd.read_csv(resolved, **kwargs)

    def save_checkpoint(self, state_dict: dict[str, Any], path: str) -> None:
        resolved = self._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        torch.save(state_dict, resolved)

    def load_checkpoint(self, path: str, map_location: str = "cpu") -> dict[str, Any]:
        resolved = self._resolve(path)
        if not resolved.exists():
            raise FileNotFoundError(f"Checkpoint 不存在: {resolved}")
        return torch.load(resolved, map_location=map_location)

    def save_tensor(self, tensor: torch.Tensor, path: str) -> None:
        resolved = self._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        torch.save(tensor, resolved)

    def save_json(self, payload: Any, path: str) -> None:
        resolved = self._resolve(path)
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def exists(self, path: str) -> bool:
        return self._resolve(path).exists()

    def makedirs(self, path: str) -> None:
        self._resolve(path).mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Cloud 实现
# ---------------------------------------------------------------------------

class CloudBackend(StorageBackend):
    """基于对象存储 SDK 的云端存储后端。

    当前以 Tencent COS 为默认实现。若需切换至 S3 / GCS，
    可扩展 ``_get_client()`` 或增加子类。
    """

    def __init__(
        self,
        cloud_config: CloudConfig,
        *,
        local_cache_dir: Path | None = None,
    ) -> None:
        self.provider = cloud_config.provider.lower()
        self.region = cloud_config.region
        self.secret_id = os.environ.get(cloud_config.secret_id_env, "")
        self.secret_key = os.environ.get(cloud_config.secret_key_env, "")
        self._local_cache = (
            local_cache_dir or Path.cwd() / ".cloud_cache"
        ).resolve()
        self._local_cache.mkdir(parents=True, exist_ok=True)
        self._client: Any = None

    def _get_client(self) -> Any:
        """按需初始化云 SDK 客户端。"""
        if self._client is not None:
            return self._client

        if self.provider == "cos":
            try:
                from qcloud_cos import CosConfig, CosS3Client
            except ImportError as exc:
                raise ImportError(
                    "云端模式需要 cos-python-sdk-v5：pip install cos-python-sdk-v5"
                ) from exc

            config = CosConfig(
                Region=self.region,
                SecretId=self.secret_id,
                SecretKey=self.secret_key,
            )
            self._client = CosS3Client(config)
            return self._client

        if self.provider == "s3":
            try:
                import boto3
            except ImportError as exc:
                raise ImportError(
                    "云端模式需要 boto3：pip install boto3"
                ) from exc
            self._client = boto3.client(
                "s3",
                region_name=self.region,
                aws_access_key_id=self.secret_id,
                aws_secret_access_key=self.secret_key,
            )
            return self._client

        raise ValueError(f"不支持的云存储提供商: {self.provider}")

    @staticmethod
    def _parse_uri(uri: str) -> tuple[str, str]:
        """将 cos://bucket/key 或 s3://bucket/key 解析为 (bucket, key)。"""
        for prefix in ("cos://", "s3://", "gs://"):
            if uri.startswith(prefix):
                remainder = uri[len(prefix):]
                parts = remainder.split("/", 1)
                bucket = parts[0]
                key = parts[1] if len(parts) > 1 else ""
                return bucket, key
        raise ValueError(f"无法解析云存储 URI: {uri}")

    def _is_cloud_uri(self, path: str) -> bool:
        return any(
            path.startswith(prefix)
            for prefix in ("cos://", "s3://", "gs://")
        )

    def _download_to_buffer(self, path: str) -> io.BytesIO:
        """从云端下载对象到内存缓冲区。"""
        bucket, key = self._parse_uri(path)
        client = self._get_client()

        if self.provider == "cos":
            response = client.get_object(Bucket=bucket, Key=key)
            body = response["Body"].get_raw_stream().read()
        elif self.provider == "s3":
            buf = io.BytesIO()
            client.download_fileobj(bucket, key, buf)
            buf.seek(0)
            return buf
        else:
            raise ValueError(f"不支持的 provider: {self.provider}")

        return io.BytesIO(body)

    def _upload_from_file(self, local_path: Path, remote_path: str) -> None:
        """将本地文件上传到云端。"""
        bucket, key = self._parse_uri(remote_path)
        client = self._get_client()

        if self.provider == "cos":
            client.upload_file(
                Bucket=bucket,
                Key=key,
                LocalFilePath=str(local_path),
            )
        elif self.provider == "s3":
            client.upload_file(str(local_path), bucket, key)
        else:
            raise ValueError(f"不支持的 provider: {self.provider}")

    # -- 接口实现 --

    def read_csv(self, path: str, **kwargs: Any) -> pd.DataFrame:
        if not self._is_cloud_uri(path):
            return pd.read_csv(path, **kwargs)
        buf = self._download_to_buffer(path)
        return pd.read_csv(buf, **kwargs)

    def save_checkpoint(self, state_dict: dict[str, Any], path: str) -> None:
        local_tmp = self._local_cache / "checkpoint_tmp.pt"
        torch.save(state_dict, local_tmp)
        if self._is_cloud_uri(path):
            self._upload_from_file(local_tmp, path)
        else:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_tmp, target)

    def load_checkpoint(self, path: str, map_location: str = "cpu") -> dict[str, Any]:
        if not self._is_cloud_uri(path):
            return torch.load(path, map_location=map_location)
        buf = self._download_to_buffer(path)
        return torch.load(buf, map_location=map_location)

    def save_tensor(self, tensor: torch.Tensor, path: str) -> None:
        local_tmp = self._local_cache / "tensor_tmp.pt"
        torch.save(tensor, local_tmp)
        if self._is_cloud_uri(path):
            self._upload_from_file(local_tmp, path)
        else:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(local_tmp, target)

    def save_json(self, payload: Any, path: str) -> None:
        content = json.dumps(payload, ensure_ascii=False, indent=2)
        local_tmp = self._local_cache / "json_tmp.json"
        local_tmp.write_text(content, encoding="utf-8")
        if self._is_cloud_uri(path):
            self._upload_from_file(local_tmp, path)
        else:
            target = Path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")

    def exists(self, path: str) -> bool:
        if not self._is_cloud_uri(path):
            return Path(path).exists()
        try:
            bucket, key = self._parse_uri(path)
            client = self._get_client()
            if self.provider == "cos":
                client.head_object(Bucket=bucket, Key=key)
            elif self.provider == "s3":
                client.head_object(Bucket=bucket, Key=key)
            return True
        except Exception:
            return False

    def makedirs(self, path: str) -> None:
        if not self._is_cloud_uri(path):
            Path(path).mkdir(parents=True, exist_ok=True)
        # 云端对象存储通常不需要显式创建目录


# ---------------------------------------------------------------------------
# 工厂函数
# ---------------------------------------------------------------------------

def create_backend(
    environment: str,
    *,
    workspace_root: Path,
    cloud_config: CloudConfig | None = None,
) -> StorageBackend:
    """根据 environment 创建对应的存储后端实例。"""
    if environment == "local":
        return LocalBackend(workspace_root)

    if environment == "cloud":
        if cloud_config is None:
            raise ValueError("云端模式需要提供 CloudConfig。")
        return CloudBackend(cloud_config)

    raise ValueError(f"未知环境: {environment}")
