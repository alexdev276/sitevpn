from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, payment_id: UUID) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def get_by_provider_payment_id(self, provider_payment_id: str) -> Payment | None:
        result = await self.session.execute(
            select(Payment).where(Payment.provider_payment_id == provider_payment_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: UUID) -> list[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.user_id == user_id).order_by(Payment.created_at.desc())
        )
        return list(result.scalars().all())

    async def list_all(self) -> list[Payment]:
        result = await self.session.execute(select(Payment).order_by(Payment.created_at.desc()))
        return list(result.scalars().all())

    async def create(self, **payload) -> Payment:
        payment = Payment(**payload)
        self.session.add(payment)
        await self.session.flush()
        return payment
