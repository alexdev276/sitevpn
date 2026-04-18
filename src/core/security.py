from __future__ import annotations

from datetime import UTC, datetime, timedelta
from secrets import token_urlsafe
from typing import Any
from uuid import uuid4

import jwt
from passlib.context import CryptContext

from src.core.config import Settings
from src.domain.enums import TokenType


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def utcnow() -> datetime:
    return datetime.now(UTC)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(settings: Settings, subject: str, role: str) -> str:
    expires_at = utcnow() + timedelta(minutes=settings.jwt_access_ttl_minutes)
    payload = {
        "sub": subject,
        "role": role,
        "type": TokenType.ACCESS.value,
        "exp": expires_at,
        "iat": utcnow(),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm="HS256")


def create_refresh_token(settings: Settings, subject: str) -> tuple[str, str]:
    expires_at = utcnow() + timedelta(days=settings.jwt_refresh_ttl_days)
    jti = str(uuid4())
    payload = {
        "sub": subject,
        "type": TokenType.REFRESH.value,
        "exp": expires_at,
        "iat": utcnow(),
        "jti": jti,
    }
    return jwt.encode(payload, settings.jwt_refresh_secret_key, algorithm="HS256"), jti


def decode_token(token: str, secret: str) -> dict[str, Any]:
    return jwt.decode(token, secret, algorithms=["HS256"])


def generate_code(length: int = 6) -> str:
    return token_urlsafe(length)[:length].upper()

