from uuid import UUID

from pathlib import Path

from fastapi import APIRouter, Depends

from src.api.v1.schemas.admin import AdminDashboardResponse, LogResponse, TariffAdminResponse, TariffCreateRequest
from src.application.vpn_service import VpnService
from src.core.config import Settings, get_settings
from src.core.dependencies import get_current_admin, get_vpn_service
from src.db.session import get_db_session
from src.infrastructure.repositories.payment_repository import PaymentRepository
from src.infrastructure.repositories.tariff_repository import TariffRepository
from src.infrastructure.repositories.user_repository import UserRepository


router = APIRouter()


@router.get("/dashboard", response_model=AdminDashboardResponse)
async def admin_dashboard(
    admin=Depends(get_current_admin),
    session=Depends(get_db_session),
) -> AdminDashboardResponse:
    users = await UserRepository(session).list_all()
    payments = await PaymentRepository(session).list_all()
    return AdminDashboardResponse(users=users, payments=payments)


@router.post("/users/{user_id}/block", response_model=dict)
async def block_vpn_user(
    user_id: UUID,
    admin=Depends(get_current_admin),
    service: VpnService = Depends(get_vpn_service),
) -> dict[str, str]:
    await service.block_user(user_id)
    return {"message": "User blocked"}


@router.delete("/users/{user_id}", response_model=dict)
async def delete_vpn_user(
    user_id: UUID,
    admin=Depends(get_current_admin),
    service: VpnService = Depends(get_vpn_service),
) -> dict[str, str]:
    await service.delete_user(user_id)
    return {"message": "User deleted"}


@router.get("/logs", response_model=LogResponse)
async def get_logs(
    admin=Depends(get_current_admin),
    settings: Settings = Depends(get_settings),
) -> LogResponse:
    if not settings.app_log_file or not Path(settings.app_log_file).exists():
        return LogResponse(lines=[])
    lines = Path(settings.app_log_file).read_text(encoding="utf-8").splitlines()[-200:]
    return LogResponse(lines=lines)


@router.get("/tariffs", response_model=list[TariffAdminResponse])
async def list_tariffs(
    admin=Depends(get_current_admin),
    session=Depends(get_db_session),
) -> list[TariffAdminResponse]:
    tariffs = await TariffRepository(session).list_active()
    return [TariffAdminResponse.model_validate(tariff) for tariff in tariffs]


@router.post("/tariffs", response_model=TariffAdminResponse)
async def create_tariff(
    payload: TariffCreateRequest,
    admin=Depends(get_current_admin),
    session=Depends(get_db_session),
) -> TariffAdminResponse:
    tariff = await TariffRepository(session).create(**payload.model_dump())
    await session.commit()
    return TariffAdminResponse.model_validate(tariff)
