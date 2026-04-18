from fastapi import FastAPI
from slowapi.errors import RateLimitExceeded

from src.api.router import api_router
from src.core.config import get_settings
from src.core.exceptions import api_exception_handler, rate_limit_handler
from src.core.logging import configure_logging
from src.core.middleware import register_middlewares
from src.core.rate_limit import limiter


settings = get_settings()
configure_logging(settings)

app = FastAPI(
    title=settings.app_name,
    debug=settings.app_debug,
    version="0.1.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)
app.state.limiter = limiter
app.add_exception_handler(Exception, api_exception_handler)
app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
register_middlewares(app)
app.include_router(api_router, prefix="/api")


@app.get("/health", tags=["system"])
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}

