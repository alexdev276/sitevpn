from uuid import UUID

from pydantic import BaseModel

from src.api.v1.schemas.common import PaymentRead


class CreatePaymentRequest(BaseModel):
    tariff_id: UUID


class PaymentCheckoutResponse(PaymentRead):
    checkout_url: str

