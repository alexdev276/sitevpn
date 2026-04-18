from fastapi import APIRouter, Depends, Request, Response

from src.api.v1.schemas.auth import (
    ChangePasswordRequest,
    ConfirmEmailRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordConfirmRequest,
    ResetPasswordRequest,
    TokenResponse,
)
from src.api.v1.schemas.common import MessageResponse
from src.application.auth_service import AuthService
from src.core.config import Settings, get_settings
from src.core.dependencies import get_auth_service, get_current_user, get_refresh_cookie
from src.core.exceptions import UnauthorizedException
from src.core.rate_limit import limiter


router = APIRouter()


@router.post("/register", response_model=MessageResponse)
@limiter.limit("5/minute")
async def register(
    request: Request,
    payload: RegisterRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.register(payload.email, payload.password)
    return MessageResponse(message="Registration successful. Verification code sent.")


@router.post("/confirm-email", response_model=MessageResponse)
async def confirm_email(
    payload: ConfirmEmailRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.confirm_email(payload.email, payload.code)
    return MessageResponse(message="Email confirmed.")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    tokens = await service.login(payload.email, payload.password)
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=tokens["refresh_token"],
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.jwt_refresh_ttl_days * 86400,
    )
    return TokenResponse(access_token=tokens["access_token"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    refresh_token: str | None = Depends(get_refresh_cookie),
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> TokenResponse:
    if refresh_token is None:
        raise UnauthorizedException("Missing refresh token")
    tokens = await service.refresh_tokens(refresh_token)
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=tokens["refresh_token"],
        httponly=True,
        secure=settings.secure_cookies,
        samesite="lax",
        max_age=settings.jwt_refresh_ttl_days * 86400,
    )
    return TokenResponse(access_token=tokens["access_token"])


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    refresh_token: str | None = Depends(get_refresh_cookie),
    service: AuthService = Depends(get_auth_service),
    settings: Settings = Depends(get_settings),
) -> MessageResponse:
    await service.logout(refresh_token)
    response.delete_cookie(settings.refresh_cookie_name)
    return MessageResponse(message="Logged out.")


@router.post("/password-reset/request", response_model=MessageResponse)
@limiter.limit("5/minute")
async def request_password_reset(
    request: Request,
    payload: ResetPasswordRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.request_password_reset(payload.email)
    return MessageResponse(message="If the email exists, reset instructions were sent.")


@router.post("/password-reset/confirm", response_model=MessageResponse)
async def confirm_password_reset(
    payload: ResetPasswordConfirmRequest,
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.reset_password(payload.email, payload.code, payload.new_password)
    return MessageResponse(message="Password updated.")


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> MessageResponse:
    await service.change_password(current_user.id, payload.current_password, payload.new_password)
    return MessageResponse(message="Password changed.")
