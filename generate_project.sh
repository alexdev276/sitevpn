#!/bin/bash

# Скрипт генерации проекта VPN-сервиса
# Запускать в пустой директории

set -e

echo "Создание структуры директорий..."

mkdir -p src/{domain,application,infrastructure/repositories,api/v1,core,db,tasks}
mkdir -p tests

echo "Генерация файлов..."

# .env.example
cat > .env.example << 'EOF'
# Application
APP_NAME=VPN Service
APP_VERSION=1.0.0
DEBUG=false
ENVIRONMENT=production
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=30

# Database
DATABASE_URL=postgresql+asyncpg://user:password@db:5432/vpn_db
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=10

# Redis
REDIS_URL=redis://redis:6379/0
REDIS_MAX_CONNECTIONS=50

# Remnawave API
REMNAWAVE_API_URL=https://panel.example.com/api
REMNAWAVE_API_KEY=your-remnawave-api-key
REMNAWAVE_SQUAD_ID=your-internal-squad-id

# Payment (Stripe)
STRIPE_API_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
PAYMENT_PROVIDER=stripe
STRIPE_SUCCESS_URL=https://example.com/success
STRIPE_CANCEL_URL=https://example.com/cancel

# Email (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=your-email@gmail.com
SMTP_USE_TLS=true

# CORS
CORS_ORIGINS=["http://localhost:3000","https://example.com"]

# Rate Limiting
RATE_LIMIT_PER_SECOND=10
RATE_LIMIT_PER_MINUTE=200

# Brute Force Protection
MAX_LOGIN_ATTEMPTS=5
LOGIN_BLOCK_TIME_MINUTES=15

# Celery
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# Admin
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=admin123
EOF

# requirements.txt
cat > requirements.txt << 'EOF'
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-dotenv==1.0.1
pydantic==2.10.5
pydantic-settings==2.7.0
SQLAlchemy==2.0.36
asyncpg==0.30.0
alembic==1.14.1
redis==5.2.1
celery==5.4.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.20
email-validator==2.2.0
httpx==0.28.1
structlog==24.4.0
slowapi==0.1.9
remnawave==0.1.0
stripe==11.3.0
aiosmtplib==3.0.2
pytest==8.3.4
pytest-asyncio==0.24.0
pytest-mock==3.14.0
faker==33.3.0
EOF

# pyproject.toml
cat > pyproject.toml << 'EOF'
[tool.poetry]
name = "vpn-service"
version = "1.0.0"
description = "Commercial VPN Service with Remnawave integration"
authors = ["Your Name <email@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115.6"
uvicorn = {extras = ["standard"], version = "^0.34.0"}
python-dotenv = "^1.0.1"
pydantic = "^2.10.5"
pydantic-settings = "^2.7.0"
SQLAlchemy = "^2.0.36"
asyncpg = "^0.30.0"
alembic = "^1.14.1"
redis = "^5.2.1"
celery = "^5.4.0"
python-jose = {extras = ["cryptography"], version = "^3.3.0"}
passlib = {extras = ["bcrypt"], version = "^1.7.4"}
python-multipart = "^0.0.20"
email-validator = "^2.2.0"
httpx = "^0.28.1"
structlog = "^24.4.0"
slowapi = "^0.1.9"
remnawave = "^0.1.0"
stripe = "^11.3.0"
aiosmtplib = "^3.0.2"

[tool.poetry.group.dev.dependencies]
pytest = "^8.3.4"
pytest-asyncio = "^0.24.0"
pytest-mock = "^3.14.0"
faker = "^33.3.0"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
EOF

# docker-compose.yml
cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  db:
    image: postgres:16-alpine
    container_name: vpn_db
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-vpn_user}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-vpn_pass}
      POSTGRES_DB: ${POSTGRES_DB:-vpn_db}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U vpn_user -d vpn_db"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - vpn_network

  redis:
    image: redis:7-alpine
    container_name: vpn_redis
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - vpn_network

  app:
    build: .
    container_name: vpn_app
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - ./src:/app/src
    ports:
      - "8000:8000"
    env_file:
      - .env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - vpn_network

  celery-worker:
    build: .
    container_name: vpn_celery_worker
    command: celery -A src.tasks.celery_app worker --loglevel=info
    volumes:
      - ./src:/app/src
    env_file:
      - .env
    depends_on:
      - redis
      - db
    networks:
      - vpn_network

  celery-beat:
    build: .
    container_name: vpn_celery_beat
    command: celery -A src.tasks.celery_app beat --loglevel=info
    volumes:
      - ./src:/app/src
    env_file:
      - .env
    depends_on:
      - redis
      - db
    networks:
      - vpn_network

volumes:
  postgres_data:
  redis_data:

networks:
  vpn_network:
    driver: bridge
EOF

# Dockerfile
cat > Dockerfile << 'EOF'
FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000
EOF

# README.md
cat > README.md << 'EOF'
# VPN Service with Remnawave Integration

## Quick Start

1. Clone repository and copy `.env.example` to `.env`, fill in your values.
2. Run `docker-compose up -d`
3. Access API docs at http://localhost:8000/docs

## Environment Variables

See `.env.example` for all required variables. Important:
- `REMNAWAVE_API_URL` and `REMNAWAVE_API_KEY` from your Remnawave panel.
- `STRIPE_API_KEY` and `STRIPE_WEBHOOK_SECRET` from Stripe dashboard.
- `SMTP_*` for email sending.

## Running Migrations

Alembic is configured. Run inside app container:
docker-compose exec app alembic upgrade head

## Testing

Run tests:

docker-compose exec app pytest

## Architecture

- Clean Architecture with separation of domain, application, infrastructure, and API layers.
- Async SQLAlchemy, Redis for caching/rate limiting.
- Celery for background tasks (email, subscription renewal).
- JWT authentication with refresh tokens in httpOnly cookies.
- Stripe payment integration (easily replaceable).

## API Endpoints

See Swagger at `/docs` for full list.

## Admin

Default admin credentials can be set via `.env`. After first run, change password.
EOF

# Теперь файлы исходного кода

# src/main.py
cat > src/main.py << 'EOF'
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import structlog
from structlog.stdlib import LoggerFactory

from src.core.config import settings
from src.core.logging import setup_logging
from src.core.exceptions import setup_exception_handlers
from src.api.v1 import router as api_v1_router
from src.db.session import engine, async_session
from src.db.base import Base
from src.infrastructure.redis_client import redis_client

setup_logging()
logger = structlog.get_logger()

limiter = Limiter(key_func=get_remote_address, default_limits=[
    f"{settings.RATE_LIMIT_PER_SECOND}/second",
    f"{settings.RATE_LIMIT_PER_MINUTE}/minute"
])

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting VPN Service")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await redis_client.initialize()
    yield
    # Shutdown
    await redis_client.close()
    await engine.dispose()
    logger.info("VPN Service shutdown")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
setup_exception_handlers(app)

# Routers
app.include_router(api_v1_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
EOF

# src/core/config.py
cat > src/core/config.py << 'EOF'
from typing import List, Optional
from pydantic import AnyHttpUrl, EmailStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # App
    APP_NAME: str = "VPN Service"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: str = "production"
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 30

    # Database
    DATABASE_URL: str
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    # Redis
    REDIS_URL: str
    REDIS_MAX_CONNECTIONS: int = 50

    # Remnawave
    REMNAWAVE_API_URL: AnyHttpUrl
    REMNAWAVE_API_KEY: str
    REMNAWAVE_SQUAD_ID: str

    # Payment
    STRIPE_API_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None
    PAYMENT_PROVIDER: str = "stripe"
    STRIPE_SUCCESS_URL: str
    STRIPE_CANCEL_URL: str

    # Email
    SMTP_HOST: str
    SMTP_PORT: int
    SMTP_USER: str
    SMTP_PASSWORD: str
    SMTP_FROM: EmailStr
    SMTP_USE_TLS: bool = True

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            return json.loads(v)
        return v

    # Rate Limiting
    RATE_LIMIT_PER_SECOND: int = 10
    RATE_LIMIT_PER_MINUTE: int = 200

    # Brute Force Protection
    MAX_LOGIN_ATTEMPTS: int = 5
    LOGIN_BLOCK_TIME_MINUTES: int = 15

    # Celery
    CELERY_BROKER_URL: str
    CELERY_RESULT_BACKEND: str

    # Admin
    ADMIN_EMAIL: EmailStr
    ADMIN_PASSWORD: str

settings = Settings()
EOF

# src/core/logging.py
cat > src/core/logging.py << 'EOF'
import logging
import structlog
from structlog.processors import JSONRenderer, TimeStamper, add_log_level
from structlog.stdlib import ProcessorFormatter

def setup_logging():
    timestamper = TimeStamper(fmt="iso")

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            timestamper,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = ProcessorFormatter(
        processor=JSONRenderer(),
    )

    handler = logging.StreamHandler()
    handler.setFormatter(formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").handlers = []
    logging.getLogger("uvicorn.access").propagate = True
EOF

# src/core/exceptions.py
cat > src/core/exceptions.py << 'EOF'
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import structlog

logger = structlog.get_logger()

class AppException(Exception):
    def __init__(self, status_code: int, detail: str, error_code: str = None):
        self.status_code = status_code
        self.detail = detail
        self.error_code = error_code

class NotFoundError(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status.HTTP_404_NOT_FOUND, detail, "NOT_FOUND")

class AuthenticationError(AppException):
    def __init__(self, detail: str = "Authentication failed"):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, "AUTH_ERROR")

class PermissionDeniedError(AppException):
    def __init__(self, detail: str = "Permission denied"):
        super().__init__(status.HTTP_403_FORBIDDEN, detail, "PERMISSION_DENIED")

class ValidationError(AppException):
    def __init__(self, detail: str = "Validation error"):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail, "VALIDATION_ERROR")

class PaymentError(AppException):
    def __init__(self, detail: str = "Payment processing error"):
        super().__init__(status.HTTP_402_PAYMENT_REQUIRED, detail, "PAYMENT_ERROR")

class RemnawaveError(AppException):
    def __init__(self, detail: str = "Remnawave API error"):
        super().__init__(status.HTTP_502_BAD_GATEWAY, detail, "REMNAWAVE_ERROR")

def setup_exception_handlers(app: FastAPI):
    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        logger.error(
            "App exception",
            error_code=exc.error_code,
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail, "error_code": exc.error_code},
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        logger.error(
            "HTTP exception",
            status_code=exc.status_code,
            detail=exc.detail,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.error(
            "Validation error",
            errors=exc.errors(),
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(
            "Unhandled exception",
            path=request.url.path,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )
EOF

# src/core/security.py
cat > src/core/security.py << 'EOF'
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
from jose import JWTError, jwt
from passlib.context import CryptContext
from src.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: Dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: Dict) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError:
        raise
EOF

# src/core/dependencies.py
cat > src/core/dependencies.py << 'EOF'
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
EOF

# src/db/base.py
cat > src/db/base.py << 'EOF'
from sqlalchemy.orm import declarative_base

Base = declarative_base()
EOF

# src/db/session.py
cat > src/db/session.py << 'EOF'
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from src.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=settings.DATABASE_POOL_SIZE,
    max_overflow=settings.DATABASE_MAX_OVERFLOW,
    echo=settings.DEBUG,
)

async_session = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

async def get_db() -> AsyncSession:
    async with async_session() as session:
        yield session
EOF

# src/db/models.py
cat > src/db/models.py << 'EOF'
from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Enum, ForeignKey, Numeric, Text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from src.db.base import Base
import enum

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    USER = "user"

class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    role = Column(Enum(UserRole), default=UserRole.USER)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relations
    subscriptions = relationship("Subscription", back_populates="user")
    payments = relationship("Payment", back_populates="user")
    vpn_user = relationship("VpnUser", back_populates="user", uselist=False)

class VpnUser(Base):
    __tablename__ = "vpn_users"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    remnawave_uuid = Column(String(36), unique=True, nullable=False)  # Remnawave user UUID
    is_blocked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="vpn_user")

class Tariff(Base):
    __tablename__ = "tariffs"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    duration_days = Column(Integer, nullable=False)  # 30, 90, 365
    price = Column(Numeric(10, 2), nullable=False)
    traffic_limit_gb = Column(Integer, nullable=False)  # GB
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    subscriptions = relationship("Subscription", back_populates="tariff")

class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    tariff_id = Column(Integer, ForeignKey("tariffs.id"), nullable=False)
    status = Column(Enum(SubscriptionStatus), default=SubscriptionStatus.INACTIVE)
    start_date = Column(DateTime(timezone=True))
    end_date = Column(DateTime(timezone=True))
    auto_renew = Column(Boolean, default=False)
    stripe_subscription_id = Column(String(100), unique=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="subscriptions")
    tariff = relationship("Tariff", back_populates="subscriptions")
    payments = relationship("Payment", back_populates="subscription")

class Payment(Base):
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"))
    amount = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), default="USD")
    status = Column(Enum(PaymentStatus), default=PaymentStatus.PENDING)
    stripe_payment_intent_id = Column(String(100), unique=True)
    stripe_invoice_id = Column(String(100))
    payment_method = Column(String(50))
    paid_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="payments")
    subscription = relationship("Subscription", back_populates="payments")

class VerificationCode(Base):
    __tablename__ = "verification_codes"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    code = Column(String(6), nullable=False)
    purpose = Column(String(50), nullable=False)  # email_verify, password_reset
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
EOF

# src/domain/user.py
cat > src/domain/user.py << 'EOF'
from pydantic import BaseModel, EmailStr, ConfigDict
from datetime import datetime
from typing import Optional
from enum import Enum

class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    role: UserRole = UserRole.USER
    is_active: bool = True
    is_verified: bool = False

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    full_name: Optional[str] = None

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    password: Optional[str] = None

class UserInDB(UserBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class User(UserInDB):
    pass

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class RefreshTokenRequest(BaseModel):
    refresh_token: str
EOF

# src/domain/subscription.py
cat > src/domain/subscription.py << 'EOF'
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from decimal import Decimal
from enum import Enum

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class TariffBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration_days: int
    price: Decimal
    traffic_limit_gb: int
    is_active: bool = True

class TariffCreate(TariffBase):
    pass

class TariffUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_days: Optional[int] = None
    price: Optional[Decimal] = None
    traffic_limit_gb: Optional[int] = None
    is_active: Optional[bool] = None

class TariffInDB(TariffBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class Tariff(TariffInDB):
    pass

class SubscriptionBase(BaseModel):
    user_id: int
    tariff_id: int
    status: SubscriptionStatus = SubscriptionStatus.INACTIVE
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_renew: bool = False

class SubscriptionCreate(BaseModel):
    tariff_id: int
    auto_renew: bool = False

class SubscriptionUpdate(BaseModel):
    status: Optional[SubscriptionStatus] = None
    auto_renew: Optional[bool] = None

class SubscriptionInDB(SubscriptionBase):
    id: int
    stripe_subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class Subscription(SubscriptionInDB):
    tariff: Optional[Tariff] = None

class VpnUsageStats(BaseModel):
    used_traffic_bytes: int
    total_traffic_bytes: int
    expire_at: Optional[datetime] = None
    is_active: bool
EOF

# src/domain/payment.py
cat > src/domain/payment.py << 'EOF'
from pydantic import BaseModel, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentBase(BaseModel):
    user_id: int
    subscription_id: Optional[int] = None
    amount: Decimal
    currency: str = "USD"
    status: PaymentStatus = PaymentStatus.PENDING

class PaymentCreate(BaseModel):
    tariff_id: int
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None

class PaymentInDB(PaymentBase):
    id: int
    stripe_payment_intent_id: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    payment_method: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Payment(PaymentInDB):
    pass

class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
EOF

# src/domain/vpn.py
cat > src/domain/vpn.py << 'EOF'
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class VpnUserCreate(BaseModel):
    email: str
    telegram_id: Optional[int] = None
    expire_at: Optional[datetime] = None
    traffic_limit_bytes: Optional[int] = None

class VpnUserUpdate(BaseModel):
    expire_at: Optional[datetime] = None
    traffic_limit_bytes: Optional[int] = None
    is_active: Optional[bool] = None

class VpnUserResponse(BaseModel):
    uuid: str
    username: str
    short_uuid: str
    status: str
    traffic_limit_bytes: int
    traffic_used_bytes: int
    expire_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
EOF

# src/infrastructure/redis_client.py
cat > src/infrastructure/redis_client.py << 'EOF'
from redis.asyncio import Redis, ConnectionPool
from src.core.config import settings

class RedisClient:
    def __init__(self):
        self.pool: ConnectionPool = None
        self.client: Redis = None

    async def initialize(self):
        self.pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
        self.client = Redis(connection_pool=self.pool)

    async def close(self):
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()

    async def get(self, key: str):
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: int = None):
        return await self.client.set(key, value, ex=ex)

    async def delete(self, key: str):
        return await self.client.delete(key)

    async def incr(self, key: str):
        return await self.client.incr(key)

    async def expire(self, key: str, seconds: int):
        return await self.client.expire(key, seconds)

    async def keys(self, pattern: str):
        return await self.client.keys(pattern)

redis_client = RedisClient()

async def get_redis() -> Redis:
    return redis_client.client
EOF

# src/infrastructure/brute_force.py
cat > src/infrastructure/brute_force.py << 'EOF'
from datetime import timedelta
from src.infrastructure.redis_client import get_redis
from src.core.config import settings

class BruteForceProtector:
    def __init__(self):
        self.max_attempts = settings.MAX_LOGIN_ATTEMPTS
        self.block_time = settings.LOGIN_BLOCK_TIME_MINUTES * 60

    async def _get_redis(self):
        return await anext(get_redis())

    async def is_blocked(self, identifier: str) -> bool:
        redis = await self._get_redis()
        key = f"brute_force:block:{identifier}"
        return await redis.exists(key) > 0

    async def record_failure(self, identifier: str):
        redis = await self._get_redis()
        attempts_key = f"brute_force:attempts:{identifier}"
        attempts = await redis.incr(attempts_key)
        if attempts == 1:
            await redis.expire(attempts_key, self.block_time)
        if attempts >= self.max_attempts:
            block_key = f"brute_force:block:{identifier}"
            await redis.set(block_key, "1", ex=self.block_time)
            await redis.delete(attempts_key)

    async def reset(self, identifier: str):
        redis = await self._get_redis()
        await redis.delete(f"brute_force:attempts:{identifier}")
        await redis.delete(f"brute_force:block:{identifier}")
EOF

# src/infrastructure/email_sender.py
cat > src/infrastructure/email_sender.py << 'EOF'
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from src.core.config import settings
import structlog

logger = structlog.get_logger()

class EmailSender:
    def __init__(self):
        self.host = settings.SMTP_HOST
        self.port = settings.SMTP_PORT
        self.user = settings.SMTP_USER
        self.password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM
        self.use_tls = settings.SMTP_USE_TLS

    async def send_email(self, to_email: str, subject: str, html_content: str):
        message = MIMEMultipart("alternative")
        message["From"] = self.from_email
        message["To"] = to_email
        message["Subject"] = subject

        part = MIMEText(html_content, "html")
        message.attach(part)

        try:
            await aiosmtplib.send(
                message,
                hostname=self.host,
                port=self.port,
                username=self.user,
                password=self.password,
                use_tls=self.use_tls,
            )
            logger.info("Email sent", to=to_email, subject=subject)
        except Exception as e:
            logger.error("Failed to send email", error=str(e), to=to_email)
            raise
EOF

# src/infrastructure/remnawave_client.py
cat > src/infrastructure/remnawave_client.py << 'EOF'
from typing import Optional, Dict, Any
from datetime import datetime
import remnawave
from src.core.config import settings
from src.core.exceptions import RemnawaveError
import structlog

logger = structlog.get_logger()

class RemnawaveClient:
    def __init__(self):
        self.client = remnawave.RemnaWaveAPI(
            base_url=str(settings.REMNAWAVE_API_URL),
            api_key=settings.REMNAWAVE_API_KEY,
        )
        self.squad_id = settings.REMNAWAVE_SQUAD_ID

    async def create_user(
        self,
        username: str,
        expire_at: Optional[datetime] = None,
        traffic_limit_bytes: Optional[int] = None,
        telegram_id: Optional[int] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create VPN user in Remnawave panel"""
        try:
            payload = {
                "username": username,
                "status": "ACTIVE",
                "squadId": self.squad_id,
            }
            if expire_at:
                payload["expireAt"] = expire_at.isoformat()
            if traffic_limit_bytes:
                payload["trafficLimitBytes"] = traffic_limit_bytes
            if telegram_id:
                payload["telegramId"] = telegram_id
            if email:
                payload["email"] = email

            response = await self.client.user.create_user(payload)
            logger.info("Remnawave user created", username=username, uuid=response.get("uuid"))
            return response
        except Exception as e:
            logger.error("Failed to create Remnawave user", error=str(e))
            raise RemnawaveError(f"Failed to create VPN user: {str(e)}")

    async def get_user(self, uuid: str) -> Dict[str, Any]:
        try:
            return await self.client.user.get_user(uuid)
        except Exception as e:
            logger.error("Failed to get Remnawave user", uuid=uuid, error=str(e))
            raise RemnawaveError(f"Failed to get VPN user: {str(e)}")

    async def update_user(
        self,
        uuid: str,
        expire_at: Optional[datetime] = None,
        traffic_limit_bytes: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            payload = {}
            if expire_at is not None:
                payload["expireAt"] = expire_at.isoformat() if expire_at else None
            if traffic_limit_bytes is not None:
                payload["trafficLimitBytes"] = traffic_limit_bytes
            if status is not None:
                payload["status"] = status

            response = await self.client.user.update_user(uuid, payload)
            logger.info("Remnawave user updated", uuid=uuid)
            return response
        except Exception as e:
            logger.error("Failed to update Remnawave user", uuid=uuid, error=str(e))
            raise RemnawaveError(f"Failed to update VPN user: {str(e)}")

    async def block_user(self, uuid: str) -> Dict[str, Any]:
        return await self.update_user(uuid, status="DISABLED")

    async def unblock_user(self, uuid: str) -> Dict[str, Any]:
        return await self.update_user(uuid, status="ACTIVE")

    async def delete_user(self, uuid: str) -> bool:
        try:
            await self.client.user.delete_user(uuid)
            logger.info("Remnawave user deleted", uuid=uuid)
            return True
        except Exception as e:
            logger.error("Failed to delete Remnawave user", uuid=uuid, error=str(e))
            raise RemnawaveError(f"Failed to delete VPN user: {str(e)}")

    async def get_user_stats(self, uuid: str) -> Dict[str, Any]:
        try:
            # Assume get_user returns usage stats
            user = await self.get_user(uuid)
            return {
                "used_traffic_bytes": user.get("usedTrafficBytes", 0),
                "total_traffic_bytes": user.get("trafficLimitBytes", 0),
                "expire_at": user.get("expireAt"),
                "is_active": user.get("status") == "ACTIVE",
            }
        except Exception as e:
            logger.error("Failed to get user stats", uuid=uuid, error=str(e))
            raise RemnawaveError(f"Failed to get VPN stats: {str(e)}")
EOF

# src/infrastructure/payment_provider.py
cat > src/infrastructure/payment_provider.py << 'EOF'
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from decimal import Decimal
import stripe
from src.core.config import settings
import structlog

logger = structlog.get_logger()

class PaymentProvider(ABC):
    @abstractmethod
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        metadata: Dict[str, Any],
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def retrieve_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def construct_webhook_event(self, payload: bytes, signature: str) -> Any:
        pass

    @abstractmethod
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        pass

class StripeProvider(PaymentProvider):
    def __init__(self):
        stripe.api_key = settings.STRIPE_API_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        metadata: Dict[str, Any],
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # cents
                currency=currency.lower(),
                metadata=metadata,
                automatic_payment_methods={"enabled": True},
            )
            logger.info("Stripe payment intent created", id=intent.id)
            return {
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
            }
        except stripe.StripeError as e:
            logger.error("Stripe error", error=str(e))
            raise

    async def retrieve_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        return stripe.PaymentIntent.retrieve(payment_intent_id)

    async def construct_webhook_event(self, payload: bytes, signature: str) -> Any:
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return event
        except ValueError:
            raise
        except stripe.SignatureVerificationError:
            raise

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                metadata=metadata,
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
            )
            logger.info("Stripe subscription created", id=subscription.id)
            return subscription
        except stripe.StripeError as e:
            logger.error("Stripe subscription error", error=str(e))
            raise

    async def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        try:
            return stripe.Subscription.delete(subscription_id)
        except stripe.StripeError as e:
            logger.error("Stripe cancel subscription error", error=str(e))
            raise

def get_payment_provider() -> PaymentProvider:
    if settings.PAYMENT_PROVIDER == "stripe":
        return StripeProvider()
    else:
        raise ValueError(f"Unsupported payment provider: {settings.PAYMENT_PROVIDER}")
EOF

# src/infrastructure/repositories/base.py
cat > src/infrastructure/repositories/base.py << 'EOF'
from typing import TypeVar, Generic, Type, Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from src.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def create(self, **kwargs) -> ModelType:
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance

    async def get(self, id: int) -> Optional[ModelType]:
        result = await self.session.execute(
            select(self.model).where(self.model.id == id)
        )
        return result.scalar_one_or_none()

    async def get_by(self, **kwargs) -> Optional[ModelType]:
        query = select(self.model)
        for key, value in kwargs.items():
            query = query.where(getattr(self.model, key) == value)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()

    async def list(self, skip: int = 0, limit: int = 100, **filters) -> List[ModelType]:
        query = select(self.model)
        for key, value in filters.items():
            query = query.where(getattr(self.model, key) == value)
        query = query.offset(skip).limit(limit)
        result = await self.session.execute(query)
        return result.scalars().all()

    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        await self.session.execute(
            update(self.model).where(self.model.id == id).values(**kwargs)
        )
        await self.session.flush()
        return await self.get(id)

    async def delete(self, id: int) -> bool:
        result = await self.session.execute(
            delete(self.model).where(self.model.id == id)
        )
        await self.session.flush()
        return result.rowcount > 0

    async def commit(self):
        await self.session.commit()

    async def refresh(self, instance: ModelType):
        await self.session.refresh(instance)
EOF

# src/infrastructure/repositories/user_repository.py
cat > src/infrastructure/repositories/user_repository.py << 'EOF'
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import User
from src.infrastructure.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        return await self.get_by(email=email)

    async def get_active_by_email(self, email: str) -> User | None:
        return await self.get_by(email=email, is_active=True)

    async def update_password(self, user_id: int, hashed_password: str) -> None:
        await self.update(user_id, hashed_password=hashed_password)

    async def verify_email(self, user_id: int) -> None:
        await self.update(user_id, is_verified=True)
EOF

# src/infrastructure/repositories/subscription_repository.py
cat > src/infrastructure/repositories/subscription_repository.py << 'EOF'
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import Subscription, Tariff
from src.infrastructure.repositories.base import BaseRepository
from typing import Optional, List

class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, session: AsyncSession):
        super().__init__(Subscription, session)

    async def get_active_for_user(self, user_id: int) -> Optional[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status == "active")
            .order_by(Subscription.end_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> List[Subscription]:
        return await self.list(user_id=user_id)

    async def get_with_tariff(self, subscription_id: int) -> Optional[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .join(Tariff)
            .where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

class TariffRepository(BaseRepository[Tariff]):
    def __init__(self, session: AsyncSession):
        super().__init__(Tariff, session)

    async def get_active(self) -> List[Tariff]:
        return await self.list(is_active=True)
EOF

# src/infrastructure/repositories/payment_repository.py
cat > src/infrastructure/repositories/payment_repository.py << 'EOF'
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Payment
from src.infrastructure.repositories.base import BaseRepository
from typing import List, Optional

class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Payment, session)

    async def get_by_stripe_payment_intent_id(self, payment_intent_id: str) -> Optional[Payment]:
        return await self.get_by(stripe_payment_intent_id=payment_intent_id)

    async def list_for_user(self, user_id: int, skip: int = 0, limit: int = 20) -> List[Payment]:
        return await self.list(skip=skip, limit=limit, user_id=user_id)

    async def mark_as_succeeded(self, payment_id: int, paid_at) -> None:
        await self.update(payment_id, status="succeeded", paid_at=paid_at)
EOF

# src/infrastructure/repositories/vpn_repository.py
cat > src/infrastructure/repositories/vpn_repository.py << 'EOF'
from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import VpnUser
from src.infrastructure.repositories.base import BaseRepository
from typing import Optional

class VpnUserRepository(BaseRepository[VpnUser]):
    def __init__(self, session: AsyncSession):
        super().__init__(VpnUser, session)

    async def get_by_user_id(self, user_id: int) -> Optional[VpnUser]:
        return await self.get_by(user_id=user_id)

    async def get_by_remnawave_uuid(self, uuid: str) -> Optional[VpnUser]:
        return await self.get_by(remnawave_uuid=uuid)

    async def create_for_user(self, user_id: int, remnawave_uuid: str) -> VpnUser:
        return await self.create(user_id=user_id, remnawave_uuid=remnawave_uuid)
EOF

# src/application/auth_service.py
cat > src/application/auth_service.py << 'EOF'
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
EOF

# src/application/vpn_service.py
cat > src/application/vpn_service.py << 'EOF'
import structlog
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.remnawave_client import RemnawaveClient
from src.infrastructure.repositories.vpn_repository import VpnUserRepository
from src.infrastructure.repositories.subscription_repository import SubscriptionRepository
from src.domain.vpn import VpnUserResponse
from src.db.models import User, Subscription, VpnUser
from src.core.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()

class VpnService:
    def __init__(
        self,
        session: AsyncSession,
        remnawave_client: RemnawaveClient,
    ):
        self.session = session
        self.remnawave = remnawave_client
        self.vpn_repo = VpnUserRepository(session)
        self.sub_repo = SubscriptionRepository(session)

    async def provision_vpn_user(self, user: User, subscription: Subscription) -> VpnUser:
        """Create or update VPN user based on subscription"""
        # Check if user already has VPN account
        vpn_user = await self.vpn_repo.get_by_user_id(user.id)

        # Prepare params
        expire_at = subscription.end_date
        traffic_limit_bytes = subscription.tariff.traffic_limit_gb * 1024 * 1024 * 1024

        if vpn_user:
            # Update existing
            await self.remnawave.update_user(
                uuid=vpn_user.remnawave_uuid,
                expire_at=expire_at,
                traffic_limit_bytes=traffic_limit_bytes,
                status="ACTIVE",
            )
            vpn_user.is_blocked = False
            await self.session.commit()
            logger.info("VPN user updated", user_id=user.id, uuid=vpn_user.remnawave_uuid)
        else:
            # Create new
            username = f"user_{user.id}"
            remnawave_user = await self.remnawave.create_user(
                username=username,
                email=user.email,
                expire_at=expire_at,
                traffic_limit_bytes=traffic_limit_bytes,
            )
            vpn_user = await self.vpn_repo.create_for_user(
                user_id=user.id,
                remnawave_uuid=remnawave_user["uuid"],
            )
            await self.session.commit()
            logger.info("VPN user created", user_id=user.id, uuid=remnawave_user["uuid"])

        return vpn_user

    async def deactivate_vpn_user(self, user_id: int):
        vpn_user = await self.vpn_repo.get_by_user_id(user_id)
        if vpn_user:
            await self.remnawave.block_user(vpn_user.remnawave_uuid)
            vpn_user.is_blocked = True
            await self.session.commit()
            logger.info("VPN user deactivated", user_id=user_id)

    async def reactivate_vpn_user(self, user_id: int):
        vpn_user = await self.vpn_repo.get_by_user_id(user_id)
        if vpn_user:
            await self.remnawave.unblock_user(vpn_user.remnawave_uuid)
            vpn_user.is_blocked = False
            await self.session.commit()
            logger.info("VPN user reactivated", user_id=user_id)

    async def get_vpn_usage(self, user_id: int) -> dict:
        vpn_user = await self.vpn_repo.get_by_user_id(user_id)
        if not vpn_user:
            raise NotFoundError("VPN user not found")

        stats = await self.remnawave.get_user_stats(vpn_user.remnawave_uuid)
        return stats

    async def get_config_link(self, user_id: int) -> str:
        vpn_user = await self.vpn_repo.get_by_user_id(user_id)
        if not vpn_user:
            raise NotFoundError("VPN user not found")
        # Generate subscription link (e.g., vless://...)
        # This depends on Remnawave panel configuration
        return f"{settings.REMNAWAVE_API_URL}/sub/{vpn_user.remnawave_uuid}"
EOF

# src/application/subscription_service.py
cat > src/application/subscription_service.py << 'EOF'
import structlog
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from src.domain.subscription import SubscriptionCreate, SubscriptionUpdate, TariffCreate, TariffUpdate
from src.domain.user import User
from src.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository, TariffRepository
)
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.payment_provider import get_payment_provider, PaymentProvider
from src.infrastructure.remnawave_client import RemnawaveClient
from src.application.vpn_service import VpnService
from src.db.models import Subscription, Tariff, Payment
from src.core.exceptions import ValidationError, NotFoundError, PaymentError

logger = structlog.get_logger()

class SubscriptionService:
    def __init__(
        self,
        session: AsyncSession,
        payment_provider: PaymentProvider,
        remnawave_client: RemnawaveClient,
    ):
        self.session = session
        self.sub_repo = SubscriptionRepository(session)
        self.tariff_repo = TariffRepository(session)
        self.user_repo = UserRepository(session)
        self.payment_provider = payment_provider
        self.vpn_service = VpnService(session, remnawave_client)

    # Tariff management
    async def create_tariff(self, tariff_data: TariffCreate) -> Tariff:
        tariff = await self.tariff_repo.create(**tariff_data.model_dump())
        await self.session.commit()
        return tariff

    async def update_tariff(self, tariff_id: int, tariff_data: TariffUpdate) -> Tariff:
        tariff = await self.tariff_repo.get(tariff_id)
        if not tariff:
            raise NotFoundError("Tariff not found")
        update_data = tariff_data.model_dump(exclude_unset=True)
        updated = await self.tariff_repo.update(tariff_id, **update_data)
        await self.session.commit()
        return updated

    async def list_tariffs(self, active_only: bool = True) -> List[Tariff]:
        if active_only:
            return await self.tariff_repo.get_active()
        return await self.tariff_repo.list()

    # Subscription management
    async def create_subscription(self, user: User, data: SubscriptionCreate) -> Subscription:
        # Check if user already has active subscription
        existing = await self.sub_repo.get_active_for_user(user.id)
        if existing:
            raise ValidationError("User already has an active subscription")

        tariff = await self.tariff_repo.get(data.tariff_id)
        if not tariff or not tariff.is_active:
            raise NotFoundError("Tariff not found or inactive")

        # Calculate dates
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=tariff.duration_days)

        subscription = await self.sub_repo.create(
            user_id=user.id,
            tariff_id=tariff.id,
            status="inactive",
            start_date=None,
            end_date=end_date,
            auto_renew=data.auto_renew,
        )
        await self.session.commit()
        await self.session.refresh(subscription)
        # Load tariff relationship
        subscription = await self.sub_repo.get_with_tariff(subscription.id)
        return subscription

    async def activate_subscription(self, subscription_id: int, payment: Payment):
        subscription = await self.sub_repo.get(subscription_id)
        if not subscription:
            raise NotFoundError("Subscription not found")

        now = datetime.now(timezone.utc)
        tariff = await self.tariff_repo.get(subscription.tariff_id)
        end_date = now + timedelta(days=tariff.duration_days)

        subscription.status = "active"
        subscription.start_date = now
        subscription.end_date = end_date
        payment.subscription_id = subscription.id

        # Provision VPN user
        user = await self.user_repo.get(subscription.user_id)
        await self.vpn_service.provision_vpn_user(user, subscription)

        await self.session.commit()
        logger.info("Subscription activated", subscription_id=subscription.id)

    async def cancel_subscription(self, user: User, subscription_id: int):
        subscription = await self.sub_repo.get(subscription_id)
        if not subscription or subscription.user_id != user.id:
            raise NotFoundError("Subscription not found")

        # Cancel in Stripe if exists
        if subscription.stripe_subscription_id:
            await self.payment_provider.cancel_subscription(subscription.stripe_subscription_id)

        subscription.status = "cancelled"
        subscription.auto_renew = False
        await self.session.commit()

        # Deactivate VPN access
        await self.vpn_service.deactivate_vpn_user(user.id)
        logger.info("Subscription cancelled", subscription_id=subscription.id)

    async def renew_subscription(self, subscription_id: int) -> bool:
        """Called by Celery beat to renew auto-renewable subscriptions"""
        subscription = await self.sub_repo.get(subscription_id)
        if not subscription or not subscription.auto_renew:
            return False
        if subscription.status not in ["active", "expired"]:
            return False

        # Check if expired and needs renewal (within 1 day of expiry)
        now = datetime.now(timezone.utc)
        if subscription.end_date and subscription.end_date > now + timedelta(days=1):
            return False

        tariff = await self.tariff_repo.get(subscription.tariff_id)
        user = await self.user_repo.get(subscription.user_id)

        # Attempt to charge (simplified - should create payment and handle via Stripe)
        try:
            # Create payment intent or charge customer
            # This is a simplified version; real implementation would use Stripe subscriptions
            new_end = max(now, subscription.end_date or now) + timedelta(days=tariff.duration_days)
            subscription.end_date = new_end
            subscription.status = "active"
            await self.session.commit()
            logger.info("Subscription renewed", subscription_id=subscription.id)
            return True
        except Exception as e:
            logger.error("Subscription renewal failed", subscription_id=subscription.id, error=str(e))
            subscription.auto_renew = False  # Disable auto-renew on failure
            await self.session.commit()
            return False

    async def get_user_subscription(self, user: User) -> Optional[Subscription]:
        return await self.sub_repo.get_active_for_user(user.id)

    async def get_user_subscriptions(self, user: User) -> List[Subscription]:
        return await self.sub_repo.list_for_user(user.id)
EOF

# src/application/payment_service.py
cat > src/application/payment_service.py << 'EOF'
import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from src.domain.payment import PaymentCreate
from src.domain.user import User
from src.infrastructure.repositories.payment_repository import PaymentRepository
from src.infrastructure.repositories.tariff_repository import TariffRepository
from src.infrastructure.repositories.subscription_repository import SubscriptionRepository
from src.infrastructure.payment_provider import get_payment_provider, PaymentProvider
from src.application.subscription_service import SubscriptionService
from src.infrastructure.remnawave_client import RemnawaveClient
from src.db.models import Payment, Tariff
from src.core.exceptions import NotFoundError, PaymentError, ValidationError

logger = structlog.get_logger()

class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        payment_provider: PaymentProvider,
        remnawave_client: RemnawaveClient,
    ):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.tariff_repo = TariffRepository(session)
        self.subscription_service = SubscriptionService(session, payment_provider, remnawave_client)
        self.payment_provider = payment_provider

    async def create_payment_intent(
        self, user: User, data: PaymentCreate
    ) -> Dict[str, Any]:
        tariff = await self.tariff_repo.get(data.tariff_id)
        if not tariff:
            raise NotFoundError("Tariff not found")

        # Check if user already has an active subscription
        existing = await self.subscription_service.get_user_subscription(user)
        if existing and existing.status == "active":
            raise ValidationError("User already has an active subscription")

        # Create payment record
        payment = await self.payment_repo.create(
            user_id=user.id,
            amount=tariff.price,
            currency="USD",
            status="pending",
        )
        await self.session.commit()

        # Create Stripe PaymentIntent
        metadata = {
            "user_id": str(user.id),
            "tariff_id": str(tariff.id),
            "payment_id": str(payment.id),
        }
        intent = await self.payment_provider.create_payment_intent(
            amount=tariff.price,
            currency="USD",
            metadata=metadata,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )

        # Update payment with Stripe ID
        payment.stripe_payment_intent_id = intent["payment_intent_id"]
        await self.session.commit()

        logger.info("Payment intent created", payment_id=payment.id, user_id=user.id)
        return {
            "client_secret": intent["client_secret"],
            "payment_intent_id": intent["payment_intent_id"],
            "payment_id": payment.id,
        }

    async def handle_webhook(self, payload: bytes, signature: str) -> bool:
        event = await self.payment_provider.construct_webhook_event(payload, signature)

        if event["type"] == "payment_intent.succeeded":
            await self._handle_payment_succeeded(event["data"]["object"])
        elif event["type"] == "payment_intent.payment_failed":
            await self._handle_payment_failed(event["data"]["object"])
        else:
            logger.debug("Unhandled webhook event", type=event["type"])
            return False
        return True

    async def _handle_payment_succeeded(self, payment_intent: Dict[str, Any]):
        payment_intent_id = payment_intent["id"]
        payment = await self.payment_repo.get_by_stripe_payment_intent_id(payment_intent_id)
        if not payment:
            logger.error("Payment not found for intent", intent_id=payment_intent_id)
            return

        if payment.status == "succeeded":
            return

        metadata = payment_intent.get("metadata", {})
        tariff_id = int(metadata.get("tariff_id", 0))
        user_id = int(metadata.get("user_id", 0))

        # Mark payment as succeeded
        paid_at = datetime.fromtimestamp(payment_intent["created"], tz=timezone.utc)
        await self.payment_repo.mark_as_succeeded(payment.id, paid_at)

        # Create or activate subscription
        user = await self._get_user(user_id)
        tariff = await self.tariff_repo.get(tariff_id)

        if not user or not tariff:
            logger.error("User or tariff not found for payment", payment_id=payment.id)
            return

        # Create subscription if not exists
        subscription = await self.subscription_service.create_subscription(
            user, SubscriptionCreate(tariff_id=tariff.id, auto_renew=False)
        )
        # Activate it
        await self.subscription_service.activate_subscription(subscription.id, payment)

        logger.info("Payment succeeded and subscription activated", payment_id=payment.id)

    async def _handle_payment_failed(self, payment_intent: Dict[str, Any]):
        payment_intent_id = payment_intent["id"]
        payment = await self.payment_repo.get_by_stripe_payment_intent_id(payment_intent_id)
        if payment:
            payment.status = "failed"
            await self.session.commit()
            logger.info("Payment failed", payment_id=payment.id)

    async def _get_user(self, user_id: int) -> Optional[User]:
        from src.infrastructure.repositories.user_repository import UserRepository
        repo = UserRepository(self.session)
        return await repo.get(user_id)

    async def get_user_payments(self, user: User, skip: int = 0, limit: int = 20):
        return await self.payment_repo.list_for_user(user.id, skip, limit)
EOF

# src/api/v1/__init__.py
cat > src/api/v1/__init__.py << 'EOF'
from fastapi import APIRouter
from src.api.v1 import auth, users, payments, subscriptions, admin

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(payments.router, prefix="/payments", tags=["payments"])
router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
EOF

# src/api/v1/auth.py
cat > src/api/v1/auth.py << 'EOF'
from fastapi import APIRouter, Depends, Request, Response, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from src.core.dependencies import get_db, get_brute_force_checker
from src.application.auth_service import AuthService
from src.infrastructure.email_sender import EmailSender
from src.infrastructure.brute_force import BruteForceProtector
from src.domain.user import UserCreate, UserLogin, TokenResponse
from src.db.session import get_db
from src.core.config import settings

router = APIRouter()
security = HTTPBearer(auto_error=False)

class RefreshTokenRequest(BaseModel):
    refresh_token: str

class VerifyEmailRequest(BaseModel):
    code: str

class RequestPasswordResetRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    code: str
    new_password: str

async def get_auth_service(
    session: AsyncSession = Depends(get_db),
    brute_force: BruteForceProtector = Depends(get_brute_force_checker),
) -> AuthService:
    email_sender = EmailSender()
    return AuthService(session, email_sender, brute_force)

@router.post("/register", response_model=TokenResponse)
async def register(
    user_data: UserCreate,
    auth_service: AuthService = Depends(get_auth_service),
):
    user = await auth_service.register(user_data)
    # Auto-login after registration? Return tokens? Or require verification first.
    # For simplicity, return tokens only after verification.
    # So just return success message.
    return {"message": "Registration successful. Please verify your email."}

@router.post("/login")
async def login(
    request: Request,
    response: Response,
    login_data: UserLogin,
    auth_service: AuthService = Depends(get_auth_service),
):
    ip_address = request.client.host
    tokens, refresh_token = await auth_service.login(login_data.email, login_data.password, ip_address)

    # Set refresh token in httpOnly cookie
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )
    return tokens

@router.post("/refresh")
async def refresh(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")

    tokens, new_refresh_token = await auth_service.refresh_tokens(refresh_token)
    response.set_cookie(
        key="refresh_token",
        value=new_refresh_token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="lax",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )
    return tokens

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    auth_service: AuthService = Depends(get_auth_service),
):
    # Get tokens
    auth_header = request.headers.get("Authorization")
    access_token = None
    if auth_header and auth_header.startswith("Bearer "):
        access_token = auth_header[7:]
    refresh_token = request.cookies.get("refresh_token")

    await auth_service.logout(access_token, refresh_token)
    response.delete_cookie("refresh_token")
    return {"message": "Logged out"}

@router.post("/verify-email")
async def verify_email(
    data: VerifyEmailRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.verify_email(data.code)
    return {"message": "Email verified successfully"}

@router.post("/request-password-reset")
async def request_password_reset(
    data: RequestPasswordResetRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.request_password_reset(data.email)
    return {"message": "If email exists, reset instructions sent"}

@router.post("/reset-password")
async def reset_password(
    data: ResetPasswordRequest,
    auth_service: AuthService = Depends(get_auth_service),
):
    await auth_service.reset_password(data.code, data.new_password)
    return {"message": "Password reset successfully"}
EOF

# src/api/v1/users.py
cat > src/api/v1/users.py << 'EOF'
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user, get_db
from src.domain.user import User, UserUpdate
from src.infrastructure.repositories.user_repository import UserRepository
from src.application.vpn_service import VpnService
from src.infrastructure.remnawave_client import RemnawaveClient

router = APIRouter()

@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=User)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    updated = await repo.update(current_user.id, **user_update.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(updated)
    return updated

@router.get("/me/vpn-usage")
async def get_vpn_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    remnawave = RemnawaveClient()
    vpn_service = VpnService(db, remnawave)
    stats = await vpn_service.get_vpn_usage(current_user.id)
    return stats

@router.get("/me/vpn-config")
async def get_vpn_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    remnawave = RemnawaveClient()
    vpn_service = VpnService(db, remnawave)
    link = await vpn_service.get_config_link(current_user.id)
    return {"config_url": link}
EOF

# src/api/v1/payments.py
cat > src/api/v1/payments.py << 'EOF'
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.core.dependencies import get_current_user, get_db
from src.domain.user import User
from src.domain.payment import PaymentCreate, Payment
from src.application.payment_service import PaymentService
from src.infrastructure.payment_provider import get_payment_provider
from src.infrastructure.remnawave_client import RemnawaveClient

router = APIRouter()

@router.post("/create-intent")
async def create_payment_intent(
    data: PaymentCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment_provider = get_payment_provider()
    remnawave = RemnawaveClient()
    service = PaymentService(db, payment_provider, remnawave)
    intent = await service.create_payment_intent(current_user, data)
    return intent

@router.get("/", response_model=List[Payment])
async def get_payments(
    skip: int = 0,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment_provider = get_payment_provider()
    remnawave = RemnawaveClient()
    service = PaymentService(db, payment_provider, remnawave)
    payments = await service.get_user_payments(current_user, skip, limit)
    return payments
EOF

# src/api/v1/subscriptions.py
cat > src/api/v1/subscriptions.py << 'EOF'
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from src.core.dependencies import get_current_user, get_db
from src.domain.user import User
from src.domain.subscription import SubscriptionCreate, Subscription, Tariff
from src.application.subscription_service import SubscriptionService
from src.infrastructure.payment_provider import get_payment_provider
from src.infrastructure.remnawave_client import RemnawaveClient

router = APIRouter()

@router.get("/tariffs", response_model=List[Tariff])
async def list_tariffs(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    payment_provider = get_payment_provider()
    remnawave = RemnawaveClient()
    service = SubscriptionService(db, payment_provider, remnawave)
    return await service.list_tariffs(active_only)

@router.post("/", response_model=Subscription)
async def create_subscription(
    data: SubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment_provider = get_payment_provider()
    remnawave = RemnawaveClient()
    service = SubscriptionService(db, payment_provider, remnawave)
    subscription = await service.create_subscription(current_user, data)
    return subscription

@router.get("/active", response_model=Subscription)
async def get_active_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment_provider = get_payment_provider()
    remnawave = RemnawaveClient()
    service = SubscriptionService(db, payment_provider, remnawave)
    sub = await service.get_user_subscription(current_user)
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")
    return sub

@router.post("/{subscription_id}/cancel")
async def cancel_subscription(
    subscription_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    payment_provider = get_payment_provider()
    remnawave = RemnawaveClient()
    service = SubscriptionService(db, payment_provider, remnawave)
    await service.cancel_subscription(current_user, subscription_id)
    return {"message": "Subscription cancelled"}
EOF

# src/api/v1/admin.py
cat > src/api/v1/admin.py << 'EOF'
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from src.core.dependencies import get_current_admin, get_db
from src.domain.user import User, UserRole
from src.domain.subscription import TariffCreate, TariffUpdate, Tariff
from src.domain.payment import Payment
from src.application.subscription_service import SubscriptionService
from src.application.vpn_service import VpnService
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.repositories.payment_repository import PaymentRepository
from src.infrastructure.payment_provider import get_payment_provider
from src.infrastructure.remnawave_client import RemnawaveClient

router = APIRouter()

@router.get("/users", response_model=List[User])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    email: Optional[str] = None,
    role: Optional[UserRole] = None,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    filters = {}
    if email:
        filters["email"] = email
    if role:
        filters["role"] = role
    users = await repo.list(skip=skip, limit=limit, **filters)
    return users

@router.patch("/users/{user_id}/block")
async def block_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = False
    await db.commit()
    # Also block VPN access
    remnawave = RemnawaveClient()
    vpn_service = VpnService(db, remnawave)
    await vpn_service.deactivate_vpn_user(user_id)
    return {"message": "User blocked"}

@router.patch("/users/{user_id}/unblock")
async def unblock_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    user = await repo.get(user_id)
    if not user:
        raise HTTPException(404, "User not found")
    user.is_active = True
    await db.commit()
    remnawave = RemnawaveClient()
    vpn_service = VpnService(db, remnawave)
    await vpn_service.reactivate_vpn_user(user_id)
    return {"message": "User unblocked"}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    deleted = await repo.delete(user_id)
    if not deleted:
        raise HTTPException(404, "User not found")
    await db.commit()
    return {"message": "User deleted"}

@router.get("/payments", response_model=List[Payment])
async def list_payments(
    skip: int = 0,
    limit: int = 100,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    repo = PaymentRepository(db)
    payments = await repo.list(skip=skip, limit=limit)
    return payments

@router.post("/tariffs", response_model=Tariff)
async def create_tariff(
    data: TariffCreate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    payment_provider = get_payment_provider()
    remnawave = RemnawaveClient()
    service = SubscriptionService(db, payment_provider, remnawave)
    tariff = await service.create_tariff(data)
    return tariff

@router.patch("/tariffs/{tariff_id}", response_model=Tariff)
async def update_tariff(
    tariff_id: int,
    data: TariffUpdate,
    admin: User = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    payment_provider = get_payment_provider()
    remnawave = RemnawaveClient()
    service = SubscriptionService(db, payment_provider, remnawave)
    tariff = await service.update_tariff(tariff_id, data)
    return tariff
EOF

# src/tasks/celery_app.py
cat > src/tasks/celery_app.py << 'EOF'
from celery import Celery
from src.core.config import settings

celery_app = Celery(
    "vpn_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.tasks.subscription_tasks", "src.tasks.email_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "renew-subscriptions-daily": {
            "task": "src.tasks.subscription_tasks.renew_expiring_subscriptions",
            "schedule": 86400.0,  # daily
        },
    },
)
EOF

# src/tasks/subscription_tasks.py
cat > src/tasks/subscription_tasks.py << 'EOF'
import asyncio
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.application.subscription_service import SubscriptionService
from src.infrastructure.payment_provider import get_payment_provider
from src.infrastructure.remnawave_client import RemnawaveClient
from src.infrastructure.repositories.subscription_repository import SubscriptionRepository
from src.db.models import Subscription
import structlog

logger = structlog.get_logger()

@shared_task
def renew_expiring_subscriptions():
    """Check and renew subscriptions that are due for renewal"""
    async def _run():
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            repo = SubscriptionRepository(session)
            # Find active subscriptions with auto_renew=True and end_date within next day
            # Simplified: fetch all active with auto_renew and check in Python
            subs = await repo.list(status="active", auto_renew=True)
            payment_provider = get_payment_provider()
            remnawave = RemnawaveClient()
            service = SubscriptionService(session, payment_provider, remnawave)

            for sub in subs:
                success = await service.renew_subscription(sub.id)
                if success:
                    logger.info("Subscription renewed", subscription_id=sub.id)
                else:
                    logger.info("Subscription not renewed", subscription_id=sub.id)

        await engine.dispose()

    asyncio.run(_run())
EOF

# src/tasks/email_tasks.py
cat > src/tasks/email_tasks.py << 'EOF'
from celery import shared_task
import asyncio
from src.infrastructure.email_sender import EmailSender
import structlog

logger = structlog.get_logger()

@shared_task
def send_email_task(to_email: str, subject: str, html_content: str):
    async def _send():
        sender = EmailSender()
        await sender.send_email(to_email, subject, html_content)

    asyncio.run(_send())
EOF

# tests/conftest.py
cat > tests/conftest.py << 'EOF'
import pytest
import asyncio
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from httpx import AsyncClient, ASGITransport

from src.main import app
from src.db.base import Base
from src.core.config import settings
from src.infrastructure.redis_client import redis_client
from src.infrastructure.repositories.user_repository import UserRepository
from src.core.security import get_password_hash
from src.db.models import User, Tariff
from src.db.session import get_db

# Use in-memory SQLite for tests
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

@pytest.fixture(scope="session")
def event_loop():
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
    # Override get_db dependency
    async def override_get_db():
        yield db_session
    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()

@pytest.fixture
async def test_user(db_session) -> User:
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
async def test_admin(db_session) -> User:
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
async def test_tariff(db_session) -> Tariff:
    from src.infrastructure.repositories.subscription_repository import TariffRepository
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
EOF

# tests/test_auth.py
cat > tests/test_auth.py << 'EOF'
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_register(client: AsyncClient):
    response = await client.post("/api/v1/auth/register", json={
        "email": "new@example.com",
        "password": "password123",
        "full_name": "New User"
    })
    assert response.status_code == 200
    data = response.json()
    assert "message" in data

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert response.cookies.get("refresh_token") is not None

@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    response = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "wrong"
    })
    assert response.status_code == 401
EOF

# tests/test_subscription.py
cat > tests/test_subscription.py << 'EOF'
import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient
from src.application.subscription_service import SubscriptionService
from src.domain.subscription import SubscriptionCreate

@pytest.mark.asyncio
async def test_create_subscription_flow(client: AsyncClient, test_user, test_tariff):
    # Login first to get token
    login_resp = await client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "password123"
    })
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create payment intent
    payment_resp = await client.post("/api/v1/payments/create-intent", json={
        "tariff_id": test_tariff.id,
        "success_url": "http://example.com/success",
        "cancel_url": "http://example.com/cancel"
    }, headers=headers)
    assert payment_resp.status_code == 200
    intent_data = payment_resp.json()
    assert "client_secret" in intent_data

    # Simulate webhook
    # We would need to mock Stripe webhook event, but for unit test we mock services
EOF

# tests/test_vpn_service.py
cat > tests/test_vpn_service.py << 'EOF'
import pytest
from unittest.mock import AsyncMock, patch
from src.application.vpn_service import VpnService
from src.infrastructure.remnawave_client import RemnawaveClient

@pytest.mark.asyncio
async def test_provision_vpn_user(db_session, test_user, test_tariff):
    # Create subscription
    from src.db.models import Subscription
    from datetime import datetime, timedelta, timezone

    sub = Subscription(
        user_id=test_user.id,
        tariff_id=test_tariff.id,
        status="inactive",
        end_date=datetime.now(timezone.utc) + timedelta(days=30),
    )
    db_session.add(sub)
    await db_session.commit()

    # Mock Remnawave client
    mock_remnawave = AsyncMock(spec=RemnawaveClient)
    mock_remnawave.create_user.return_value = {"uuid": "test-uuid-123"}

    service = VpnService(db_session, mock_remnawave)
    vpn_user = await service.provision_vpn_user(test_user, sub)

    assert vpn_user.remnawave_uuid == "test-uuid-123"
    mock_remnawave.create_user.assert_called_once()
EOF

echo "Генерация проекта завершена!"
echo "Теперь выполните:"
echo "  cp .env.example .env"
echo "  # отредактируйте .env"
echo "  docker-compose up -d"