from fastapi import APIRouter, Depends, Header, Request

from src.api.v1.schemas.common import MessageResponse, PaymentRead
from src.api.v1.schemas.payments import CreatePaymentRequest, PaymentCheckoutResponse
from src.application.payment_service import PaymentService
from src.core.dependencies import get_current_user, get_payment_service


router = APIRouter()


@router.post("", response_model=PaymentCheckoutResponse)
async def create_payment(
    payload: CreatePaymentRequest,
    current_user=Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
) -> PaymentCheckoutResponse:
    payment = await service.create_payment(current_user.id, payload.tariff_id)
    return PaymentCheckoutResponse.model_validate(payment)


@router.post("/webhook", response_model=MessageResponse, include_in_schema=False)
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
    service: PaymentService = Depends(get_payment_service),
) -> MessageResponse:
    await service.handle_webhook(await request.body(), stripe_signature)
    return MessageResponse(message="Webhook processed.")

