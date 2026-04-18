from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundException
from src.core.security import utcnow
from src.domain.enums import SubscriptionStatus
from src.infrastructure.repositories.subscription_repository import SubscriptionRepository
from src.infrastructure.repositories.tariff_repository import TariffRepository


class SubscriptionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.subscriptions = SubscriptionRepository(session)
        self.tariffs = TariffRepository(session)

    async def create_pending_subscription(self, user_id: UUID, tariff_id: UUID):
        tariff = await self.tariffs.get_by_id(tariff_id)
        if not tariff:
            raise NotFoundException("Tariff not found")
        existing = await self.subscriptions.get_pending_for_user(user_id)
        if existing:
            return existing
        starts_at = utcnow()
        subscription = await self.subscriptions.create(
            user_id=user_id,
            tariff_id=tariff.id,
            status=SubscriptionStatus.PENDING,
            starts_at=starts_at,
            ends_at=starts_at + timedelta(days=tariff.duration_days),
            auto_renew=True,
        )
        await self.session.flush()
        return subscription

    async def activate_subscription(self, subscription_id: UUID):
        subscription = await self.subscriptions.get_by_id(subscription_id)
        if not subscription:
            raise NotFoundException("Subscription not found")
        subscription.status = SubscriptionStatus.ACTIVE
        await self.session.commit()
        return subscription

    async def cancel_subscription(self, user_id: UUID):
        subscription = await self.subscriptions.get_active_for_user(user_id)
        if not subscription:
            raise NotFoundException("Active subscription not found")
        subscription.auto_renew = False
        subscription.status = SubscriptionStatus.CANCELED
        await self.session.commit()
        return subscription

    async def get_current_subscription(self, user_id: UUID):
        return await self.subscriptions.get_active_for_user(user_id)

