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
