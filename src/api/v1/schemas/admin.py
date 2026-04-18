from decimal import Decimal

from pydantic import BaseModel

from src.api.v1.schemas.common import PaymentRead, TariffRead, UserRead
from src.domain.enums import TariffPeriod


class AdminDashboardResponse(BaseModel):
    users: list[UserRead]
    payments: list[PaymentRead]


class LogResponse(BaseModel):
    lines: list[str]


class TariffCreateRequest(BaseModel):
    name: str
    description: str | None = None
    period: TariffPeriod
    price: Decimal
    duration_days: int
    traffic_limit_bytes: int


class TariffAdminResponse(TariffRead):
    is_active: bool

    model_config = {"from_attributes": True}
