import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.db.base import Base
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.repositories.subscription_repository import TariffRepository
from src.core.security import get_password_hash
from src.db.models import User, Tariff
from src.db.session import get_db

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
    """Переопределяем event_loop для сессии."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="function")
async def engine():
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest.fixture(scope="function")
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session

@pytest.fixture(scope="function")
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest.fixture
async def test_user(db_session: AsyncSession) -> User:
    repo = UserRepository(db_session)
    user = await repo.create(
        email="test@example.com",
        hashed_password=get_password_hash("password123"),
        full_name="Test User",
        is_verified=True,
    )
    await db_session.commit()
    return user

@pytest.fixture
async def test_admin(db_session: AsyncSession) -> User:
    repo = UserRepository(db_session)
    user = await repo.create(
        email="admin@example.com",
        hashed_password=get_password_hash("admin123"),
        full_name="Admin",
        role="admin",
        is_verified=True,
    )
    await db_session.commit()
    return user

@pytest.fixture
async def test_tariff(db_session: AsyncSession) -> Tariff:
    repo = TariffRepository(db_session)
    tariff = await repo.create(
        name="Monthly",
        duration_days=30,
        price=9.99,
        traffic_limit_gb=100,
        is_active=True,
    )
    await db_session.commit()
    return tariff