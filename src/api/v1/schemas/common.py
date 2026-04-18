from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.domain.enums import PaymentStatus, SubscriptionStatus, TariffPeriod, UserRole


class MessageResponse(BaseModel):
    message: str


class UserRead(BaseModel):
    id: UUID
    email: EmailStr
    role: UserRole
    is_active: bool
    is_email_confirmed: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class TariffRead(BaseModel):
    id: UUID
    name: str
    description: str | None = None
    period: TariffPeriod
    price: Decimal
    duration_days: int
    traffic_limit_bytes: int

    model_config = {"from_attributes": True}


class SubscriptionRead(BaseModel):
    id: UUID
    status: SubscriptionStatus
    starts_at: datetime
    ends_at: datetime
    auto_renew: bool
    tariff: TariffRead

    model_config = {"from_attributes": True}


class PaymentRead(BaseModel):
    id: UUID
    amount: Decimal
    currency: str
    status: PaymentStatus
    checkout_url: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class VpnUserRead(BaseModel):
    id: UUID
    username: str
    status: str
    used_traffic_bytes: int
    traffic_limit_bytes: int
    expires_at: datetime
    configs: dict

    model_config = {"from_attributes": True}

