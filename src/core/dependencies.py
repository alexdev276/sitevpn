from typing import Optional, Annotated
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from src.core.config import settings
from src.core.security import decode_token
from src.core.exceptions import AuthenticationError, PermissionDeniedError
from src.db.session import get_db
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.redis_client import get_redis
from src.domain.user import User

security = HTTPBearer(auto_error=False)

async def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> Optional[User]:
    if not credentials:
        return None
    token = credentials.credentials
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        user_id: str = payload.get("sub")
        if user_id is None:
            return None
    except JWTError:
        return None

    # Check if token is blacklisted
    is_blacklisted = await redis.get(f"blacklist:{token}")
    if is_blacklisted:
        return None

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(int(user_id))
    if user is None or not user.is_active:
        return None
    return user

async def get_current_user(
    current_user: Optional[User] = Depends(get_current_user_optional),
) -> User:
    if current_user is None:
        raise AuthenticationError("Not authenticated")
    return current_user

async def get_current_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise PermissionDeniedError("Admin privileges required")
    return current_user

def get_brute_force_checker():
    from src.infrastructure.brute_force import BruteForceProtector
    return BruteForceProtector()
