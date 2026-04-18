import structlog
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from decimal import Decimal

from src.domain.payment import PaymentCreate
from src.domain.user import User
from src.infrastructure.repositories.payment_repository import PaymentRepository
from src.infrastructure.repositories.tariff_repository import TariffRepository
from src.infrastructure.repositories.subscription_repository import SubscriptionRepository
from src.infrastructure.payment_provider import get_payment_provider, PaymentProvider
from src.application.subscription_service import SubscriptionService
from src.infrastructure.remnawave_client import RemnawaveClient
from src.db.models import Payment, Tariff
from src.core.exceptions import NotFoundError, PaymentError, ValidationError

logger = structlog.get_logger()

class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        payment_provider: PaymentProvider,
        remnawave_client: RemnawaveClient,
    ):
        self.session = session
        self.payment_repo = PaymentRepository(session)
        self.tariff_repo = TariffRepository(session)
        self.subscription_service = SubscriptionService(session, payment_provider, remnawave_client)
        self.payment_provider = payment_provider

    async def create_payment_intent(
        self, user: User, data: PaymentCreate
    ) -> Dict[str, Any]:
        tariff = await self.tariff_repo.get(data.tariff_id)
        if not tariff:
            raise NotFoundError("Tariff not found")

        # Check if user already has an active subscription
        existing = await self.subscription_service.get_user_subscription(user)
        if existing and existing.status == "active":
            raise ValidationError("User already has an active subscription")

        # Create payment record
        payment = await self.payment_repo.create(
            user_id=user.id,
            amount=tariff.price,
            currency="USD",
            status="pending",
        )
        await self.session.commit()

        # Create Stripe PaymentIntent
        metadata = {
            "user_id": str(user.id),
            "tariff_id": str(tariff.id),
            "payment_id": str(payment.id),
        }
        intent = await self.payment_provider.create_payment_intent(
            amount=tariff.price,
            currency="USD",
            metadata=metadata,
            success_url=data.success_url,
            cancel_url=data.cancel_url,
        )

        # Update payment with Stripe ID
        payment.stripe_payment_intent_id = intent["payment_intent_id"]
        await self.session.commit()

        logger.info("Payment intent created", payment_id=payment.id, user_id=user.id)
        return {
            "client_secret": intent["client_secret"],
            "payment_intent_id": intent["payment_intent_id"],
            "payment_id": payment.id,
        }

    async def handle_webhook(self, payload: bytes, signature: str) -> bool:
        event = await self.payment_provider.construct_webhook_event(payload, signature)

        if event["type"] == "payment_intent.succeeded":
            await self._handle_payment_succeeded(event["data"]["object"])
        elif event["type"] == "payment_intent.payment_failed":
            await self._handle_payment_failed(event["data"]["object"])
        else:
            logger.debug("Unhandled webhook event", type=event["type"])
            return False
        return True

    async def _handle_payment_succeeded(self, payment_intent: Dict[str, Any]):
        payment_intent_id = payment_intent["id"]
        payment = await self.payment_repo.get_by_stripe_payment_intent_id(payment_intent_id)
        if not payment:
            logger.error("Payment not found for intent", intent_id=payment_intent_id)
            return

        if payment.status == "succeeded":
            return

        metadata = payment_intent.get("metadata", {})
        tariff_id = int(metadata.get("tariff_id", 0))
        user_id = int(metadata.get("user_id", 0))

        # Mark payment as succeeded
        paid_at = datetime.fromtimestamp(payment_intent["created"], tz=timezone.utc)
        await self.payment_repo.mark_as_succeeded(payment.id, paid_at)

        # Create or activate subscription
        user = await self._get_user(user_id)
        tariff = await self.tariff_repo.get(tariff_id)

        if not user or not tariff:
            logger.error("User or tariff not found for payment", payment_id=payment.id)
            return

        # Create subscription if not exists
        subscription = await self.subscription_service.create_subscription(
            user, SubscriptionCreate(tariff_id=tariff.id, auto_renew=False)
        )
        # Activate it
        await self.subscription_service.activate_subscription(subscription.id, payment)

        logger.info("Payment succeeded and subscription activated", payment_id=payment.id)

    async def _handle_payment_failed(self, payment_intent: Dict[str, Any]):
        payment_intent_id = payment_intent["id"]
        payment = await self.payment_repo.get_by_stripe_payment_intent_id(payment_intent_id)
        if payment:
            payment.status = "failed"
            await self.session.commit()
            logger.info("Payment failed", payment_id=payment.id)

    async def _get_user(self, user_id: int) -> Optional[User]:
        from src.infrastructure.repositories.user_repository import UserRepository
        repo = UserRepository(self.session)
        return await repo.get(user_id)

    async def get_user_payments(self, user: User, skip: int = 0, limit: int = 20):
        return await self.payment_repo.list_for_user(user.id, skip, limit)
