from pydantic import BaseModel, ConfigDict
from datetime import datetime
from decimal import Decimal
from typing import Optional
from enum import Enum

class PaymentStatus(str, Enum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REFUNDED = "refunded"

class PaymentBase(BaseModel):
    user_id: int
    subscription_id: Optional[int] = None
    amount: Decimal
    currency: str = "USD"
    status: PaymentStatus = PaymentStatus.PENDING

class PaymentCreate(BaseModel):
    tariff_id: int
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None

class PaymentInDB(PaymentBase):
    id: int
    stripe_payment_intent_id: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    payment_method: Optional[str] = None
    paid_at: Optional[datetime] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class Payment(PaymentInDB):
    pass

class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str
