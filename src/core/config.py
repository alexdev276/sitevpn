from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = Field("VPN Service", alias="APP_NAME")
    app_env: Literal["dev", "test", "prod"] = Field("dev", alias="APP_ENV")
    app_host: str = Field("0.0.0.0", alias="APP_HOST")
    app_port: int = Field(8000, alias="APP_PORT")
    app_debug: bool = Field(False, alias="APP_DEBUG")
    app_log_level: str = Field("INFO", alias="APP_LOG_LEVEL")
    app_log_file: str | None = Field(None, alias="APP_LOG_FILE")
    cors_origins: list[str] = Field(default_factory=list, alias="CORS_ORIGINS")
    cors_allow_credentials: bool = Field(True, alias="CORS_ALLOW_CREDENTIALS")

    database_url: str = Field(..., alias="DATABASE_URL")
    redis_url: str = Field(..., alias="REDIS_URL")

    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_refresh_secret_key: str = Field(..., alias="JWT_REFRESH_SECRET_KEY")
    jwt_access_ttl_minutes: int = Field(15, alias="JWT_ACCESS_TTL_MINUTES")
    jwt_refresh_ttl_days: int = Field(30, alias="JWT_REFRESH_TTL_DAYS")
    refresh_cookie_name: str = Field("refresh_token", alias="REFRESH_COOKIE_NAME")
    secure_cookies: bool = Field(False, alias="SECURE_COOKIES")

    brute_force_max_attempts: int = Field(5, alias="BRUTE_FORCE_MAX_ATTEMPTS")
    brute_force_block_minutes: int = Field(15, alias="BRUTE_FORCE_BLOCK_MINUTES")

    stripe_secret_key: str = Field(..., alias="STRIPE_SECRET_KEY")
    stripe_webhook_secret: str = Field(..., alias="STRIPE_WEBHOOK_SECRET")
    stripe_api_base: str = Field("https://api.stripe.com", alias="STRIPE_API_BASE")
    stripe_success_url: str = Field(..., alias="STRIPE_SUCCESS_URL")
    stripe_cancel_url: str = Field(..., alias="STRIPE_CANCEL_URL")

    remnawave_base_url: str = Field(..., alias="REMNAWAVE_BASE_URL")
    remnawave_api_key: str = Field(..., alias="REMNAWAVE_API_KEY")
    remnawave_internal_squad_id: str = Field(..., alias="REMNAWAVE_INTERNAL_SQUAD_ID")
    default_traffic_limit_bytes: int = Field(
        107374182400,
        alias="DEFAULT_TRAFFIC_LIMIT_BYTES",
    )

    email_from: str = Field(..., alias="EMAIL_FROM")
    smtp_host: str = Field(..., alias="SMTP_HOST")
    smtp_port: int = Field(1025, alias="SMTP_PORT")
    smtp_username: str | None = Field(None, alias="SMTP_USERNAME")
    smtp_password: str | None = Field(None, alias="SMTP_PASSWORD")
    admin_email: str = Field(..., alias="ADMIN_EMAIL")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
