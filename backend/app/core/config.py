"""应用配置定义。"""

from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    """统一管理应用运行时配置。"""

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # MySQL
    mysql_host: str = Field(default="127.0.0.1", validation_alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, validation_alias="MYSQL_PORT")
    mysql_database: str = Field(validation_alias="MYSQL_DATABASE")
    mysql_user: str = Field(validation_alias="MYSQL_USER")
    mysql_password: str = Field(validation_alias="MYSQL_PASSWORD")
    mysql_root_password: str = Field(validation_alias="MYSQL_ROOT_PASSWORD")

    # MinIO
    minio_endpoint: str = Field(
        default="127.0.0.1:9000", validation_alias="MINIO_ENDPOINT"
    )
    minio_root_user: str = Field(validation_alias="MINIO_ROOT_USER")
    minio_root_password: str = Field(validation_alias="MINIO_ROOT_PASSWORD")
    minio_secure: bool = Field(default=False, validation_alias="MINIO_SECURE")

    # Redis
    redis_host: str = Field(default="127.0.0.1", validation_alias="REDIS_HOST")
    redis_port: int = Field(default=6379, validation_alias="REDIS_PORT")
    redis_db: int = Field(default=0, validation_alias="REDIS_DB")
    redis_password: str | None = Field(default=None, validation_alias="REDIS_PASSWORD")

    # Auth
    auth_token_secret: str = Field(
        default="flowbeat-dev-secret-change-me",
        validation_alias="AUTH_TOKEN_SECRET",
    )
    auth_token_issuer: str = Field(
        default="flowbeat-backend",
        validation_alias="AUTH_TOKEN_ISSUER",
    )
    password_hash_iterations: int = Field(
        default=390000,
        validation_alias="PASSWORD_HASH_ITERATIONS",
    )

    # CORS
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        validation_alias="CORS_ALLOW_ORIGINS",
    )

    @property
    def sqlalchemy_database_uri(self) -> str:
        """SQLAlchemy 异步连接串（用于应用与 Alembic）。"""
        user = quote_plus(self.mysql_user)
        password = quote_plus(self.mysql_password)
        database = quote_plus(self.mysql_database)
        return (
            f"mysql+asyncmy://{user}:{password}@"
            f"{self.mysql_host}:{self.mysql_port}/{database}?charset=utf8mb4"
        )

    @property
    def redis_uri(self) -> str:
        """Redis 异步连接串。"""
        auth = ""
        if self.redis_password:
            auth = f":{quote_plus(self.redis_password)}@"
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


@lru_cache
def get_settings() -> Settings:
    """缓存配置实例，避免重复读取环境变量。"""
    return Settings()  # pyright: ignore[reportCallIssue]


settings = get_settings()
