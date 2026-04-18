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
