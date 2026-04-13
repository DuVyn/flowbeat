"""鉴权与密码安全工具。"""

from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

from app.core.config import settings


class SecurityError(ValueError):
    """安全校验失败。"""


@dataclass(slots=True)
class TokenPayload:
    """Bearer Token 解码后的核心载荷。"""

    user_id: int
    session_id: int
    token_type: str
    exp: int
    iss: str


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _decode_payload_dict(payload_b64: str) -> dict[str, Any]:
    """解码并校验 Token 载荷必须为对象结构。"""
    try:
        payload_raw = _b64url_decode(payload_b64)
    except (binascii.Error, ValueError) as exc:
        raise SecurityError("Token 载荷编码无效") from exc

    try:
        payload_obj = json.loads(payload_raw)
    except json.JSONDecodeError as exc:
        raise SecurityError("Token 载荷无效") from exc

    if not isinstance(payload_obj, dict):
        raise SecurityError("Token 载荷结构无效")
    return payload_obj


def hash_password(password: str) -> str:
    """使用 PBKDF2-HMAC-SHA256 对密码做单向哈希。"""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        settings.password_hash_iterations,
    )
    return (
        f"pbkdf2_sha256${settings.password_hash_iterations}${salt.hex()}${digest.hex()}"
    )


def verify_password(password: str, stored_hash: str) -> bool:
    """校验明文密码与数据库哈希是否匹配。"""
    try:
        algorithm, iterations_raw, salt_hex, digest_hex = stored_hash.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        expected_digest = bytes.fromhex(digest_hex)
        derived_digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt_hex),
            iterations,
        )
        return hmac.compare_digest(derived_digest, expected_digest)
    except (TypeError, ValueError):
        return False


def hash_token(token: str) -> str:
    """刷新令牌只存哈希，避免明文落库。"""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def generate_msno() -> str:
    """生成本地用户的业务唯一标识。"""
    return f"local_{secrets.token_hex(16)}"


def calculate_age(birthday: date, today: date | None = None) -> int:
    """基于生日计算年龄；若生日晚于今天则抛错。"""
    current_date = today or datetime.now(timezone.utc).date()
    if birthday > current_date:
        raise SecurityError("生日不能晚于当前日期")

    age = current_date.year - birthday.year
    if (current_date.month, current_date.day) < (birthday.month, birthday.day):
        age -= 1
    return max(age, 0)


def create_auth_token(
    *,
    user_id: int,
    session_id: int,
    token_type: str,
    expires_at: datetime,
) -> str:
    """创建 HMAC 签名的无状态令牌。"""
    payload: dict[str, Any] = {
        "sub": user_id,
        "sid": session_id,
        "typ": token_type,
        "exp": int(expires_at.timestamp()),
        "iss": settings.auth_token_issuer,
    }
    payload_b64 = _b64url_encode(
        json.dumps(
            payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
    )
    signature = hmac.new(
        settings.auth_token_secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    signature_b64 = _b64url_encode(signature)
    return f"{payload_b64}.{signature_b64}"


def decode_auth_token(token: str, *, expected_token_type: str) -> TokenPayload:
    """校验令牌签名、有效期与令牌类型。"""
    try:
        payload_b64, signature_b64 = token.split(".", 1)
    except ValueError as exc:
        raise SecurityError("Token 格式不正确") from exc

    expected_signature = hmac.new(
        settings.auth_token_secret.encode("utf-8"),
        payload_b64.encode("ascii"),
        hashlib.sha256,
    ).digest()
    try:
        actual_signature = _b64url_decode(signature_b64)
    except Exception as exc:
        raise SecurityError("Token 签名格式无效") from exc
    if not hmac.compare_digest(expected_signature, actual_signature):
        raise SecurityError("Token 签名无效")

    payload_obj = _decode_payload_dict(payload_b64)
    try:
        payload = TokenPayload(
            user_id=int(payload_obj["sub"]),
            session_id=int(payload_obj["sid"]),
            token_type=str(payload_obj["typ"]),
            exp=int(payload_obj["exp"]),
            iss=str(payload_obj["iss"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise SecurityError("Token 载荷字段无效") from exc

    now_ts = int(datetime.now(timezone.utc).timestamp())
    if payload.exp <= now_ts:
        raise SecurityError("Token 已过期")
    if payload.iss != settings.auth_token_issuer:
        raise SecurityError("Token 签发方不匹配")
    if payload.token_type != expected_token_type:
        raise SecurityError("Token 类型不匹配")
    return payload
