import structlog
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from src.domain.subscription import SubscriptionCreate, SubscriptionUpdate, TariffCreate, TariffUpdate
from src.domain.user import User
from src.infrastructure.repositories.subscription_repository import (
    SubscriptionRepository, TariffRepository
)
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.payment_provider import get_payment_provider, PaymentProvider
from src.infrastructure.remnawave_client import RemnawaveClient
from src.application.vpn_service import VpnService
from src.db.models import Subscription, Tariff, Payment
from src.core.exceptions import ValidationError, NotFoundError, PaymentError

logger = structlog.get_logger()

class SubscriptionService:
    def __init__(
        self,
        session: AsyncSession,
        payment_provider: PaymentProvider,
        remnawave_client: RemnawaveClient,
    ):
        self.session = session
        self.sub_repo = SubscriptionRepository(session)
        self.tariff_repo = TariffRepository(session)
        self.user_repo = UserRepository(session)
        self.payment_provider = payment_provider
        self.vpn_service = VpnService(session, remnawave_client)

    # Tariff management
    async def create_tariff(self, tariff_data: TariffCreate) -> Tariff:
        tariff = await self.tariff_repo.create(**tariff_data.model_dump())
        await self.session.commit()
        return tariff

    async def update_tariff(self, tariff_id: int, tariff_data: TariffUpdate) -> Tariff:
        tariff = await self.tariff_repo.get(tariff_id)
        if not tariff:
            raise NotFoundError("Tariff not found")
        update_data = tariff_data.model_dump(exclude_unset=True)
        updated = await self.tariff_repo.update(tariff_id, **update_data)
        await self.session.commit()
        return updated

    async def list_tariffs(self, active_only: bool = True) -> List[Tariff]:
        if active_only:
            return await self.tariff_repo.get_active()
        return await self.tariff_repo.list()

    # Subscription management
    async def create_subscription(self, user: User, data: SubscriptionCreate) -> Subscription:
        # Check if user already has active subscription
        existing = await self.sub_repo.get_active_for_user(user.id)
        if existing:
            raise ValidationError("User already has an active subscription")

        tariff = await self.tariff_repo.get(data.tariff_id)
        if not tariff or not tariff.is_active:
            raise NotFoundError("Tariff not found or inactive")

        # Calculate dates
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=tariff.duration_days)

        subscription = await self.sub_repo.create(
            user_id=user.id,
            tariff_id=tariff.id,
            status="inactive",
            start_date=None,
            end_date=end_date,
            auto_renew=data.auto_renew,
        )
        await self.session.commit()
        await self.session.refresh(subscription)
        # Load tariff relationship
        subscription = await self.sub_repo.get_with_tariff(subscription.id)
        return subscription

    async def activate_subscription(self, subscription_id: int, payment: Payment):
        subscription = await self.sub_repo.get(subscription_id)
        if not subscription:
            raise NotFoundError("Subscription not found")

        now = datetime.now(timezone.utc)
        tariff = await self.tariff_repo.get(subscription.tariff_id)
        end_date = now + timedelta(days=tariff.duration_days)

        subscription.status = "active"
        subscription.start_date = now
        subscription.end_date = end_date
        payment.subscription_id = subscription.id

        # Provision VPN user
        user = await self.user_repo.get(subscription.user_id)
        await self.vpn_service.provision_vpn_user(user, subscription)

        await self.session.commit()
        logger.info("Subscription activated", subscription_id=subscription.id)

    async def cancel_subscription(self, user: User, subscription_id: int):
        subscription = await self.sub_repo.get(subscription_id)
        if not subscription or subscription.user_id != user.id:
            raise NotFoundError("Subscription not found")

        # Cancel in Stripe if exists
        if subscription.stripe_subscription_id:
            await self.payment_provider.cancel_subscription(subscription.stripe_subscription_id)

        subscription.status = "cancelled"
        subscription.auto_renew = False
        await self.session.commit()

        # Deactivate VPN access
        await self.vpn_service.deactivate_vpn_user(user.id)
        logger.info("Subscription cancelled", subscription_id=subscription.id)

    async def renew_subscription(self, subscription_id: int) -> bool:
        """Called by Celery beat to renew auto-renewable subscriptions"""
        subscription = await self.sub_repo.get(subscription_id)
        if not subscription or not subscription.auto_renew:
            return False
        if subscription.status not in ["active", "expired"]:
            return False

        # Check if expired and needs renewal (within 1 day of expiry)
        now = datetime.now(timezone.utc)
        if subscription.end_date and subscription.end_date > now + timedelta(days=1):
            return False

        tariff = await self.tariff_repo.get(subscription.tariff_id)
        user = await self.user_repo.get(subscription.user_id)

        # Attempt to charge (simplified - should create payment and handle via Stripe)
        try:
            # Create payment intent or charge customer
            # This is a simplified version; real implementation would use Stripe subscriptions
            new_end = max(now, subscription.end_date or now) + timedelta(days=tariff.duration_days)
            subscription.end_date = new_end
            subscription.status = "active"
            await self.session.commit()
            logger.info("Subscription renewed", subscription_id=subscription.id)
            return True
        except Exception as e:
            logger.error("Subscription renewal failed", subscription_id=subscription.id, error=str(e))
            subscription.auto_renew = False  # Disable auto-renew on failure
            await self.session.commit()
            return False

    async def get_user_subscription(self, user: User) -> Optional[Subscription]:
        return await self.sub_repo.get_active_for_user(user.id)

    async def get_user_subscriptions(self, user: User) -> List[Subscription]:
        return await self.sub_repo.list_for_user(user.id)
