from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.application.subscription_service import SubscriptionService
from src.application.vpn_service import VpnService
from src.core.config import Settings
from src.core.exceptions import AppException, NotFoundException
from src.domain.enums import PaymentProviderType, PaymentStatus, TariffPeriod
from src.infrastructure.payments.base import PaymentProvider
from src.infrastructure.repositories.payment_repository import PaymentRepository
from src.infrastructure.repositories.subscription_repository import SubscriptionRepository
from src.infrastructure.repositories.tariff_repository import TariffRepository


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        settings: Settings,
        payment_provider: PaymentProvider,
    ) -> None:
        self.session = session
        self.settings = settings
        self.provider = payment_provider
        self.payments = PaymentRepository(session)
        self.subscriptions = SubscriptionRepository(session)
        self.tariffs = TariffRepository(session)
        self.subscription_service = SubscriptionService(session)
        self.vpn_service = VpnService(session, settings)

    async def create_payment(self, user_id: UUID, tariff_id: UUID):
        tariff = await self.tariffs.get_by_id(tariff_id)
        if not tariff:
            raise NotFoundException("Tariff not found")
        subscription = await self.subscription_service.create_pending_subscription(user_id, tariff_id)
        recurring_interval = {
            TariffPeriod.MONTHLY: "month",
            TariffPeriod.QUARTERLY: "month",
            TariffPeriod.YEARLY: "year",
        }[tariff.period]
        description = f"{tariff.name} VPN subscription"
        checkout = await self.provider.create_checkout_session(
            amount=Decimal(tariff.price),
            currency="USD",
            description=description,
            metadata={
                "user_id": str(user_id),
                "tariff_id": str(tariff.id),
                "subscription_id": str(subscription.id),
            },
            recurring_interval=recurring_interval,
        )
        payment = await self.payments.create(
            user_id=user_id,
            subscription_id=subscription.id,
            amount=tariff.price,
            currency="USD",
            provider=PaymentProviderType.STRIPE,
            provider_payment_id=checkout.payment_id,
            provider_subscription_id=checkout.subscription_id,
            checkout_url=checkout.checkout_url,
            provider_payload=checkout.raw or {},
        )
        await self.session.commit()
        return payment

    async def handle_webhook(self, payload: bytes, signature: str | None) -> None:
        event = await self.provider.parse_webhook(payload, signature)
        payment = await self.payments.get_by_provider_payment_id(event.provider_payment_id)
        if not payment and event.metadata.get("subscription_id"):
            raise NotFoundException("Payment not found")
        if event.event_type not in {"checkout.session.completed", "invoice.paid"}:
            return
        if not payment:
            raise AppException("Webhook metadata is incomplete", 400, "bad_webhook")
        payment.status = PaymentStatus.SUCCEEDED
        if event.provider_subscription_id:
            payment.provider_subscription_id = event.provider_subscription_id
        subscription = await self.subscription_service.activate_subscription(payment.subscription_id)
        await self.vpn_service.ensure_vpn_user(payment.user_id, subscription)
        await self.session.commit()

    async def cancel_subscription(self, user_id: UUID) -> None:
        subscription = await self.subscriptions.get_active_for_user(user_id)
        if not subscription:
            raise NotFoundException("Active subscription not found")
        payment_list = await self.payments.list_for_user(user_id)
        provider_subscription_id = next(
            (payment.provider_subscription_id for payment in payment_list if payment.provider_subscription_id),
            None,
        )
        if provider_subscription_id:
            await self.provider.cancel_subscription(provider_subscription_id)
        await self.subscription_service.cancel_subscription(user_id)
