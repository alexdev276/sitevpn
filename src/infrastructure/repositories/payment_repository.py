from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import Payment
from src.infrastructure.repositories.base import BaseRepository
from typing import List, Optional

class PaymentRepository(BaseRepository[Payment]):
    def __init__(self, session: AsyncSession):
        super().__init__(Payment, session)

    async def get_by_stripe_payment_intent_id(self, payment_intent_id: str) -> Optional[Payment]:
        return await self.get_by(stripe_payment_intent_id=payment_intent_id)

    async def list_for_user(self, user_id: int, skip: int = 0, limit: int = 20) -> List[Payment]:
        return await self.list(skip=skip, limit=limit, user_id=user_id)

    async def mark_as_succeeded(self, payment_id: int, paid_at) -> None:
        await self.update(payment_id, status="succeeded", paid_at=paid_at)
