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
