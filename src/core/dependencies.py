from __future__ import annotations

from uuid import UUID

from fastapi import Cookie, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from src.application.auth_service import AuthService
from src.application.payment_service import PaymentService
from src.application.subscription_service import SubscriptionService
from src.application.user_service import UserService
from src.application.vpn_service import VpnService
from src.core.config import Settings, get_settings
from src.core.exceptions import ForbiddenException, UnauthorizedException
from src.core.security import decode_token
from src.db.session import get_db_session
from src.domain.enums import TokenType, UserRole
from src.infrastructure.payments.stripe_provider import StripePaymentProvider
from src.infrastructure.redis import redis_client
from src.infrastructure.repositories.user_repository import UserRepository


bearer_scheme = HTTPBearer(auto_error=False)


def get_redis() -> Redis:
    return redis_client


def get_auth_service(
    session: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    settings: Settings = Depends(get_settings),
) -> AuthService:
    return AuthService(session, redis, settings)


def get_payment_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> PaymentService:
    return PaymentService(session, settings, StripePaymentProvider(settings))


def get_subscription_service(
    session: AsyncSession = Depends(get_db_session),
) -> SubscriptionService:
    return SubscriptionService(session)


def get_vpn_service(
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> VpnService:
    return VpnService(session, settings)


def get_user_service(
    session: AsyncSession = Depends(get_db_session),
) -> UserService:
    return UserService(session)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
):
    if not credentials:
        raise UnauthorizedException("Missing access token")
    payload = decode_token(credentials.credentials, settings.jwt_secret_key)
    if payload["type"] != TokenType.ACCESS.value:
        raise UnauthorizedException("Invalid token type")
    user = await UserRepository(session).get_by_id(UUID(payload["sub"]))
    if not user:
        raise UnauthorizedException("User not found")
    return user


async def get_current_admin(user=Depends(get_current_user)):
    if user.role != UserRole.ADMIN:
        raise ForbiddenException("Admin access required")
    return user


async def get_refresh_cookie(
    settings: Settings = Depends(get_settings),
    refresh_token: str | None = Cookie(default=None, alias="refresh_token"),
) -> str | None:
    return refresh_token

