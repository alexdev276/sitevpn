from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.exceptions import NotFoundException
from src.infrastructure.repositories.payment_repository import PaymentRepository
from src.infrastructure.repositories.subscription_repository import SubscriptionRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.repositories.vpn_repository import VpnRepository


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.payments = PaymentRepository(session)
        self.vpn_users = VpnRepository(session)

    async def get_dashboard(self, user_id: UUID) -> dict:
        user = await self.users.get_by_id(user_id)
        if not user:
            raise NotFoundException("User not found")
        subscription = await self.subscriptions.get_active_for_user(user_id)
        vpn_user = await self.vpn_users.get_by_user_id(user_id)
        payments = await self.payments.list_for_user(user_id)
        return {
            "user": user,
            "subscription": subscription,
            "vpn_user": vpn_user,
            "payments": payments,
        }

