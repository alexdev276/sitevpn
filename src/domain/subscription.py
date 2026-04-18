from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional
from decimal import Decimal
from enum import Enum

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

class TariffBase(BaseModel):
    name: str
    description: Optional[str] = None
    duration_days: int
    price: Decimal
    traffic_limit_gb: int
    is_active: bool = True

class TariffCreate(TariffBase):
    pass

class TariffUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_days: Optional[int] = None
    price: Optional[Decimal] = None
    traffic_limit_gb: Optional[int] = None
    is_active: Optional[bool] = None

class TariffInDB(TariffBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class Tariff(TariffInDB):
    pass

class SubscriptionBase(BaseModel):
    user_id: int
    tariff_id: int
    status: SubscriptionStatus = SubscriptionStatus.INACTIVE
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    auto_renew: bool = False

class SubscriptionCreate(BaseModel):
    tariff_id: int
    auto_renew: bool = False

class SubscriptionUpdate(BaseModel):
    status: Optional[SubscriptionStatus] = None
    auto_renew: Optional[bool] = None

class SubscriptionInDB(SubscriptionBase):
    id: int
    stripe_subscription_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    model_config = ConfigDict(from_attributes=True)

class Subscription(SubscriptionInDB):
    tariff: Optional[Tariff] = None

class VpnUsageStats(BaseModel):
    used_traffic_bytes: int
    total_traffic_bytes: int
    expire_at: Optional[datetime] = None
    is_active: bool
