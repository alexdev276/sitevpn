from fastapi import APIRouter

from src.api.v1.endpoints import admin, auth, payments, subscriptions, users


api_router = APIRouter()
api_router.include_router(auth.router, prefix="/v1/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/v1/users", tags=["users"])
api_router.include_router(payments.router, prefix="/v1/payments", tags=["payments"])
api_router.include_router(subscriptions.router, prefix="/v1/subscriptions", tags=["subscriptions"])
api_router.include_router(admin.router, prefix="/v1/admin", tags=["admin"])

