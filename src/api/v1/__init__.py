from fastapi import APIRouter
from src.api.v1 import auth, users, payments, subscriptions, admin

router = APIRouter()
router.include_router(auth.router, prefix="/auth", tags=["auth"])
router.include_router(users.router, prefix="/users", tags=["users"])
router.include_router(payments.router, prefix="/payments", tags=["payments"])
router.include_router(subscriptions.router, prefix="/subscriptions", tags=["subscriptions"])
router.include_router(admin.router, prefix="/admin", tags=["admin"])
