from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class VpnUserCreate(BaseModel):
    email: str
    telegram_id: Optional[int] = None
    expire_at: Optional[datetime] = None
    traffic_limit_bytes: Optional[int] = None

class VpnUserUpdate(BaseModel):
    expire_at: Optional[datetime] = None
    traffic_limit_bytes: Optional[int] = None
    is_active: Optional[bool] = None

class VpnUserResponse(BaseModel):
    uuid: str
    username: str
    short_uuid: str
    status: str
    traffic_limit_bytes: int
    traffic_used_bytes: int
    expire_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
