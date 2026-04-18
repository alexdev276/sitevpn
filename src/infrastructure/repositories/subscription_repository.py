from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Subscription
from src.domain.enums import SubscriptionStatus


class SubscriptionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, subscription_id: UUID) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.tariff))
            .where(Subscription.id == subscription_id)
        )
        return result.scalar_one_or_none()

    async def get_active_for_user(self, user_id: UUID) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.tariff))
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.ACTIVE,
            )
        )
        return result.scalar_one_or_none()

    async def get_pending_for_user(self, user_id: UUID) -> Subscription | None:
        result = await self.session.execute(
            select(Subscription)
            .options(selectinload(Subscription.tariff))
            .where(
                Subscription.user_id == user_id,
                Subscription.status == SubscriptionStatus.PENDING,
            )
        )
        return result.scalar_one_or_none()

    async def list_due_for_renewal(self, now: datetime) -> list[Subscription]:
        result = await self.session.execute(
            select(Subscription).where(
                Subscription.auto_renew.is_(True),
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.ends_at <= now,
            )
        )
        return list(result.scalars().all())

    async def create(self, **payload) -> Subscription:
        subscription = Subscription(**payload)
        self.session.add(subscription)
        await self.session.flush()
        return subscription
