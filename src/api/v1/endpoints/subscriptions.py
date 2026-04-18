from fastapi import APIRouter, Depends

from src.api.v1.schemas.common import MessageResponse, SubscriptionRead
from src.application.payment_service import PaymentService
from src.application.subscription_service import SubscriptionService
from src.core.dependencies import get_current_user, get_payment_service, get_subscription_service


router = APIRouter()


@router.get("/current", response_model=SubscriptionRead | None)
async def current_subscription(
    current_user=Depends(get_current_user),
    service: SubscriptionService = Depends(get_subscription_service),
):
    return await service.get_current_subscription(current_user.id)


@router.post("/cancel", response_model=MessageResponse)
async def cancel_subscription(
    current_user=Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> MessageResponse:
    await service.cancel_subscription(current_user.id)
    return MessageResponse(message="Subscription canceled.")

