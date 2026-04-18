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
