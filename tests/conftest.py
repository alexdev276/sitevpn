from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
import os

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret")
os.environ.setdefault("JWT_REFRESH_SECRET_KEY", "test-refresh-secret")
os.environ.setdefault("STRIPE_SECRET_KEY", "test")
os.environ.setdefault("STRIPE_WEBHOOK_SECRET", "test")
os.environ.setdefault("STRIPE_SUCCESS_URL", "http://test/success")
os.environ.setdefault("STRIPE_CANCEL_URL", "http://test/cancel")
os.environ.setdefault("REMNAWAVE_BASE_URL", "https://example.invalid")
os.environ.setdefault("REMNAWAVE_API_KEY", "test")
os.environ.setdefault("REMNAWAVE_INTERNAL_SQUAD_ID", "squad")
os.environ.setdefault("EMAIL_FROM", "test@example.com")
os.environ.setdefault("SMTP_HOST", "localhost")
os.environ.setdefault("ADMIN_EMAIL", "admin@example.com")

from src.core.config import get_settings
from src.core.dependencies import get_redis
from src.db.base import Base
from src.db.session import get_db_session
from src.main import app


TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


class FakeRedis:
    def __init__(self) -> None:
        self.storage: dict[str, str] = {}

    async def flushdb(self) -> None:
        self.storage.clear()

    async def setex(self, key: str, _: int, value: str) -> None:
        self.storage[key] = value

    async def get(self, key: str) -> str | None:
        return self.storage.get(key)

    async def delete(self, *keys: str) -> None:
        for key in keys:
            self.storage.pop(key, None)

    async def incr(self, key: str) -> int:
        current = int(self.storage.get(key, "0")) + 1
        self.storage[key] = str(current)
        return current

    async def expire(self, key: str, _: int) -> None:
        self.storage.setdefault(key, self.storage.get(key, "0"))

    async def close(self) -> None:
        return None


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(TEST_DATABASE_URL, future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def redis_mock() -> AsyncGenerator[FakeRedis, None]:
    client = FakeRedis()
    await client.flushdb()
    yield client
    await client.flushdb()
    await client.close()


@pytest.fixture
async def test_app(db_session: AsyncSession, redis_mock: FakeRedis) -> FastAPI:
    async def override_db():
        yield db_session

    def override_redis():
        return redis_mock

    app.dependency_overrides[get_db_session] = override_db
    app.dependency_overrides[get_redis] = override_redis
    yield app
    app.dependency_overrides.clear()


@pytest.fixture
def settings():
    return get_settings()


@pytest.fixture
async def client(test_app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as http_client:
        yield http_client
