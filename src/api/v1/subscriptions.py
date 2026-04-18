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
