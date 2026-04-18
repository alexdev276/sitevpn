from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import VpnUser
from src.infrastructure.repositories.base import BaseRepository
from typing import Optional

class VpnUserRepository(BaseRepository[VpnUser]):
    def __init__(self, session: AsyncSession):
        super().__init__(VpnUser, session)

    async def get_by_user_id(self, user_id: int) -> Optional[VpnUser]:
        return await self.get_by(user_id=user_id)

    async def get_by_remnawave_uuid(self, uuid: str) -> Optional[VpnUser]:
        return await self.get_by(remnawave_uuid=uuid)

    async def create_for_user(self, user_id: int, remnawave_uuid: str) -> VpnUser:
        return await self.create(user_id=user_id, remnawave_uuid=remnawave_uuid)
