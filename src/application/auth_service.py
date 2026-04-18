from __future__ import annotations

from uuid import UUID

import structlog
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.exceptions import AppException, ConflictException, UnauthorizedException
from src.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_code,
    hash_password,
    utcnow,
    verify_password,
)
from src.domain.enums import TokenType, UserRole
from src.infrastructure.repositories.user_repository import UserRepository


logger = structlog.get_logger(__name__)


class AuthService:
    def __init__(self, session: AsyncSession, redis: Redis, settings: Settings) -> None:
        self.session = session
        self.redis = redis
        self.settings = settings
        self.users = UserRepository(session)

    async def register(self, email: str, password: str) -> None:
        email = email.lower()
        existing = await self.users.get_by_email(email)
        if existing:
            raise ConflictException("User with this email already exists")

        await self.users.create(
            email=email,
            password_hash=hash_password(password),
            role=UserRole.USER,
        )
        code = generate_code()
        await self.redis.setex(f"verify:{email}", 900, code)
        self._enqueue_email_code(email, code, "email_verification")
        await self.session.commit()
        logger.info("user_registered", email=email, verification_code=code)

    async def confirm_email(self, email: str, code: str) -> None:
        email = email.lower()
        cached_code = await self.redis.get(f"verify:{email}")
        if cached_code != code.upper():
            raise AppException("Invalid verification code", 400, "invalid_code")
        user = await self.users.get_by_email(email)
        if not user:
            raise UnauthorizedException("User not found")
        user.is_email_confirmed = True
        await self.redis.delete(f"verify:{email}")
        await self.session.commit()

    async def login(self, email: str, password: str) -> dict[str, str]:
        email = email.lower()
        await self._ensure_not_blocked(f"login:{email}")
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            await self._register_failed_attempt(f"login:{email}")
            raise UnauthorizedException("Invalid credentials")
        if not user.is_email_confirmed:
            raise UnauthorizedException("Email is not confirmed")
        access_token = create_access_token(self.settings, str(user.id), user.role.value)
        refresh_token, refresh_jti = create_refresh_token(self.settings, str(user.id))
        await self.redis.setex(
            f"refresh:{refresh_jti}",
            self.settings.jwt_refresh_ttl_days * 86400,
            str(user.id),
        )
        await self.redis.delete(f"attempts:login:{email}")
        return {"access_token": access_token, "refresh_token": refresh_token}

    async def refresh_tokens(self, refresh_token: str) -> dict[str, str]:
        payload = decode_token(refresh_token, self.settings.jwt_refresh_secret_key)
        if payload["type"] != TokenType.REFRESH.value:
            raise UnauthorizedException("Invalid refresh token type")
        jti = payload["jti"]
        user_id = payload["sub"]
        exists = await self.redis.get(f"refresh:{jti}")
        if not exists:
            raise UnauthorizedException("Refresh token expired or revoked")
        user = await self.users.get_by_id(UUID(user_id))
        if not user:
            raise UnauthorizedException("User not found")
        await self.redis.delete(f"refresh:{jti}")
        access_token = create_access_token(self.settings, str(user.id), user.role.value)
        new_refresh_token, new_jti = create_refresh_token(self.settings, str(user.id))
        await self.redis.setex(
            f"refresh:{new_jti}",
            self.settings.jwt_refresh_ttl_days * 86400,
            str(user.id),
        )
        return {"access_token": access_token, "refresh_token": new_refresh_token}

    async def logout(self, refresh_token: str | None) -> None:
        if not refresh_token:
            return
        payload = decode_token(refresh_token, self.settings.jwt_refresh_secret_key)
        await self.redis.delete(f"refresh:{payload['jti']}")

    async def request_password_reset(self, email: str) -> None:
        email = email.lower()
        await self._ensure_not_blocked(f"reset:{email}")
        user = await self.users.get_by_email(email)
        if not user:
            await self._register_failed_attempt(f"reset:{email}")
            return
        code = generate_code()
        await self.redis.setex(f"reset:{email}", 900, code)
        self._enqueue_email_code(email, code, "password_reset")
        logger.info("password_reset_requested", email=email, reset_code=code)

    async def reset_password(self, email: str, code: str, new_password: str) -> None:
        email = email.lower()
        cached_code = await self.redis.get(f"reset:{email}")
        if cached_code != code.upper():
            raise AppException("Invalid reset code", 400, "invalid_code")
        user = await self.users.get_by_email(email)
        if not user:
            raise UnauthorizedException("User not found")
        user.password_hash = hash_password(new_password)
        await self.redis.delete(f"reset:{email}")
        await self.session.commit()

    async def change_password(self, user_id: UUID, current_password: str, new_password: str) -> None:
        user = await self.users.get_by_id(user_id)
        if not user or not verify_password(current_password, user.password_hash):
            raise UnauthorizedException("Current password is invalid")
        user.password_hash = hash_password(new_password)
        await self.session.commit()

    async def _ensure_not_blocked(self, key: str) -> None:
        blocked_until = await self.redis.get(f"blocked:{key}")
        if blocked_until:
            raise AppException(
                "Too many failed attempts. Try again later.",
                429,
                "too_many_attempts",
            )

    async def _register_failed_attempt(self, key: str) -> None:
        attempts_key = f"attempts:{key}"
        attempts = await self.redis.incr(attempts_key)
        if attempts == 1:
            await self.redis.expire(attempts_key, self.settings.brute_force_block_minutes * 60)
        if attempts >= self.settings.brute_force_max_attempts:
            await self.redis.setex(
                f"blocked:{key}",
                self.settings.brute_force_block_minutes * 60,
                utcnow().isoformat(),
            )

    def _enqueue_email_code(self, email: str, code: str, purpose: str) -> None:
        try:
            from src.tasks.jobs import send_email_code

            send_email_code.delay(email, code, purpose)
        except Exception as exc:  # pragma: no cover
            logger.warning("email_task_enqueue_failed", email=email, purpose=purpose, error=str(exc))
