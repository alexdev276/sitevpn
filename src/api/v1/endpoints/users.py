from fastapi import APIRouter, Depends

from src.api.v1.schemas.users import DashboardResponse
from src.application.user_service import UserService
from src.core.dependencies import get_current_user, get_user_service


router = APIRouter()


@router.get("/me", response_model=DashboardResponse)
async def get_profile(
    current_user=Depends(get_current_user),
    service: UserService = Depends(get_user_service),
) -> DashboardResponse:
    dashboard = await service.get_dashboard(current_user.id)
    return DashboardResponse(
        **DashboardResponse.model_validate(dashboard["user"]).model_dump(),
        subscription=dashboard["subscription"],
        vpn_user=dashboard["vpn_user"],
        payments=dashboard["payments"],
    )

