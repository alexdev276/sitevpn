import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from src.core.security import (
    verify_password, get_password_hash, create_access_token, create_refresh_token, decode_token
)
from src.core.config import settings
from src.core.exceptions import AuthenticationError, ValidationError, NotFoundError
from src.domain.user import UserCreate, User, TokenResponse
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.repositories.base import BaseRepository
from src.db.models import VerificationCode, User as UserModel
from src.infrastructure.email_sender import EmailSender
from src.infrastructure.redis_client import get_redis
from src.infrastructure.brute_force import BruteForceProtector

logger = structlog.get_logger()

class AuthService:
    def __init__(
        self,
        session: AsyncSession,
        email_sender: EmailSender,
        brute_force: BruteForceProtector,
    ):
        self.session = session
        self.user_repo = UserRepository(session)
        self.code_repo = BaseRepository(VerificationCode, session)
        self.email_sender = email_sender
        self.brute_force = brute_force

    async def register(self, user_data: UserCreate) -> User:
        # Check if user exists
        existing = await self.user_repo.get_by_email(user_data.email)
        if existing:
            raise ValidationError("User with this email already exists")

        # Create user
        hashed = get_password_hash(user_data.password)
        user = await self.user_repo.create(
            email=user_data.email,
            hashed_password=hashed,
            full_name=user_data.full_name,
            is_verified=False,
        )
        await self.session.commit()
        await self.session.refresh(user)

        # Send verification email
        await self._send_verification_email(user)

        logger.info("User registered", user_id=user.id, email=user.email)
        return User.model_validate(user)

    async def login(self, email: str, password: str, ip_address: str) -> Tuple[TokenResponse, str]:
        # Check brute force
        if await self.brute_force.is_blocked(f"email:{email}"):
            raise AuthenticationError("Too many failed attempts. Try again later.")
        if await self.brute_force.is_blocked(f"ip:{ip_address}"):
            raise AuthenticationError("Too many failed attempts from this IP.")

        user = await self.user_repo.get_active_by_email(email)
        if not user or not verify_password(password, user.hashed_password):
            await self.brute_force.record_failure(f"email:{email}")
            await self.brute_force.record_failure(f"ip:{ip_address}")
            raise AuthenticationError("Invalid email or password")

        if not user.is_verified:
            raise AuthenticationError("Email not verified")

        # Reset brute force
        await self.brute_force.reset(f"email:{email}")
        await self.brute_force.reset(f"ip:{ip_address}")

        # Create tokens
        access_token = create_access_token({"sub": str(user.id)})
        refresh_token = create_refresh_token({"sub": str(user.id)})

        logger.info("User logged in", user_id=user.id, email=user.email)
        return TokenResponse(access_token=access_token), refresh_token

    async def refresh_tokens(self, refresh_token: str) -> Tuple[TokenResponse, str]:
        try:
            payload = decode_token(refresh_token)
            if payload.get("type") != "refresh":
                raise AuthenticationError("Invalid token type")
            user_id = int(payload.get("sub"))
        except Exception:
            raise AuthenticationError("Invalid refresh token")

        user = await self.user_repo.get(user_id)
        if not user or not user.is_active:
            raise AuthenticationError("User not found or inactive")

        # Check if token is blacklisted (optional)
        # ...

        new_access = create_access_token({"sub": str(user.id)})
        new_refresh = create_refresh_token({"sub": str(user.id)})

        return TokenResponse(access_token=new_access), new_refresh

    async def logout(self, access_token: str, refresh_token: Optional[str] = None):
        # Blacklist tokens
        redis = await anext(get_redis())
        # For simplicity, just blacklist access token with expiry
        # In production, use proper token blacklist
        await redis.setex(f"blacklist:{access_token}", settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60, "1")
        if refresh_token:
            await redis.setex(f"blacklist:{refresh_token}", settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400, "1")
        logger.info("User logged out")

    async def verify_email(self, code: str) -> bool:
        verification = await self.code_repo.get_by(code=code, purpose="email_verify", used=False)
        if not verification or verification.expires_at < datetime.now(timezone.utc):
            raise ValidationError("Invalid or expired verification code")

        user = await self.user_repo.get(verification.user_id)
        if not user:
            raise NotFoundError("User not found")

        user.is_verified = True
        verification.used = True
        await self.session.commit()
        logger.info("Email verified", user_id=user.id)
        return True

    async def request_password_reset(self, email: str):
        user = await self.user_repo.get_by_email(email)
        if not user:
            # Don't reveal existence
            return
        await self._send_password_reset_email(user)

    async def reset_password(self, code: str, new_password: str):
        verification = await self.code_repo.get_by(code=code, purpose="password_reset", used=False)
        if not verification or verification.expires_at < datetime.now(timezone.utc):
            raise ValidationError("Invalid or expired reset code")

        user = await self.user_repo.get(verification.user_id)
        if not user:
            raise NotFoundError("User not found")

        hashed = get_password_hash(new_password)
        user.hashed_password = hashed
        verification.used = True
        await self.session.commit()
        logger.info("Password reset", user_id=user.id)

    async def _send_verification_email(self, user: UserModel):
        code = secrets.token_urlsafe(32)[:6]
        expires = datetime.now(timezone.utc) + timedelta(hours=24)
        await self.code_repo.create(
            user_id=user.id,
            code=code,
            purpose="email_verify",
            expires_at=expires,
        )
        await self.session.commit()

        # Send email
        subject = "Verify your email"
        html = f"Your verification code: {code}"
        await self.email_sender.send_email(user.email, subject, html)

    async def _send_password_reset_email(self, user: UserModel):
        code = secrets.token_urlsafe(32)[:6]
        expires = datetime.now(timezone.utc) + timedelta(hours=1)
        await self.code_repo.create(
            user_id=user.id,
            code=code,
            purpose="password_reset",
            expires_at=expires,
        )
        await self.session.commit()

        subject = "Password Reset"
        html = f"Your password reset code: {code}"
        await self.email_sender.send_email(user.email, subject, html)
