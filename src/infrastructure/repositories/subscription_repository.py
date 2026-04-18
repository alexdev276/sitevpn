from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from src.db.models import Subscription, Tariff
from src.infrastructure.repositories.base import BaseRepository
from typing import Optional, List

class SubscriptionRepository(BaseRepository[Subscription]):
    def __init__(self, session: AsyncSession):
        super().__init__(Subscription, session)

    async def get_active_for_user(self, user_id: int) -> Optional[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .where(Subscription.user_id == user_id)
            .where(Subscription.status == "active")
            .order_by(Subscription.end_date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: int) -> List[Subscription]:
        return await self.list(user_id=user_id)

    async def get_with_tariff(self, subscription_id: int) -> Optional[Subscription]:
        result = await self.session.execute(
            select(Subscription)
            .join(Tariff)
            .where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

class TariffRepository(BaseRepository[Tariff]):
    def __init__(self, session: AsyncSession):
        super().__init__(Tariff, session)

    async def get_active(self) -> List[Tariff]:
        return await self.list(is_active=True)
