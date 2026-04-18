from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import VpnUser


class VpnRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_user_id(self, user_id: UUID) -> VpnUser | None:
        result = await self.session.execute(select(VpnUser).where(VpnUser.user_id == user_id))
        return result.scalar_one_or_none()

    async def create(self, **payload) -> VpnUser:
        vpn_user = VpnUser(**payload)
        self.session.add(vpn_user)
        await self.session.flush()
        return vpn_user

