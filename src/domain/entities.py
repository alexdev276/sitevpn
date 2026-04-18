from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from src.domain.enums import PaymentStatus, SubscriptionStatus, TariffPeriod, UserRole


@dataclass(slots=True)
class UserEntity:
    id: UUID
    email: str
    role: UserRole
    is_active: bool
    is_email_confirmed: bool
    created_at: datetime


@dataclass(slots=True)
class TariffEntity:
    id: UUID
    name: str
    period: TariffPeriod
    price: Decimal
    traffic_limit_bytes: int
    duration_days: int


@dataclass(slots=True)
class SubscriptionEntity:
    id: UUID
    user_id: UUID
    tariff_id: UUID
    status: SubscriptionStatus
    starts_at: datetime
    ends_at: datetime


@dataclass(slots=True)
class PaymentEntity:
    id: UUID
    user_id: UUID
    amount: Decimal
    status: PaymentStatus
    external_id: str | None

