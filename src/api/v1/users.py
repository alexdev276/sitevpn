from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.dependencies import get_current_user, get_db
from src.domain.user import User, UserUpdate
from src.infrastructure.repositories.user_repository import UserRepository
from src.application.vpn_service import VpnService
from src.infrastructure.remnawave_client import RemnawaveClient

router = APIRouter()

@router.get("/me", response_model=User)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.patch("/me", response_model=User)
async def update_me(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    repo = UserRepository(db)
    updated = await repo.update(current_user.id, **user_update.model_dump(exclude_unset=True))
    await db.commit()
    await db.refresh(updated)
    return updated

@router.get("/me/vpn-usage")
async def get_vpn_usage(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    remnawave = RemnawaveClient()
    vpn_service = VpnService(db, remnawave)
    stats = await vpn_service.get_vpn_usage(current_user.id)
    return stats

@router.get("/me/vpn-config")
async def get_vpn_config(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    remnawave = RemnawaveClient()
    vpn_service = VpnService(db, remnawave)
    link = await vpn_service.get_config_link(current_user.id)
    return {"config_url": link}
