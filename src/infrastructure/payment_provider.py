from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from decimal import Decimal
import stripe
from src.core.config import settings
import structlog

logger = structlog.get_logger()

class PaymentProvider(ABC):
    @abstractmethod
    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        metadata: Dict[str, Any],
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def retrieve_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def construct_webhook_event(self, payload: bytes, signature: str) -> Any:
        pass

    @abstractmethod
    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        pass

class StripeProvider(PaymentProvider):
    def __init__(self):
        stripe.api_key = settings.STRIPE_API_KEY
        self.webhook_secret = settings.STRIPE_WEBHOOK_SECRET

    async def create_payment_intent(
        self,
        amount: Decimal,
        currency: str,
        metadata: Dict[str, Any],
        success_url: Optional[str] = None,
        cancel_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            intent = stripe.PaymentIntent.create(
                amount=int(amount * 100),  # cents
                currency=currency.lower(),
                metadata=metadata,
                automatic_payment_methods={"enabled": True},
            )
            logger.info("Stripe payment intent created", id=intent.id)
            return {
                "client_secret": intent.client_secret,
                "payment_intent_id": intent.id,
            }
        except stripe.StripeError as e:
            logger.error("Stripe error", error=str(e))
            raise

    async def retrieve_payment_intent(self, payment_intent_id: str) -> Dict[str, Any]:
        return stripe.PaymentIntent.retrieve(payment_intent_id)

    async def construct_webhook_event(self, payload: bytes, signature: str) -> Any:
        try:
            event = stripe.Webhook.construct_event(
                payload, signature, self.webhook_secret
            )
            return event
        except ValueError:
            raise
        except stripe.SignatureVerificationError:
            raise

    async def create_subscription(
        self,
        customer_id: str,
        price_id: str,
        metadata: Dict[str, Any],
    ) -> Dict[str, Any]:
        try:
            subscription = stripe.Subscription.create(
                customer=customer_id,
                items=[{"price": price_id}],
                metadata=metadata,
                payment_behavior="default_incomplete",
                expand=["latest_invoice.payment_intent"],
            )
            logger.info("Stripe subscription created", id=subscription.id)
            return subscription
        except stripe.StripeError as e:
            logger.error("Stripe subscription error", error=str(e))
            raise

    async def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        try:
            return stripe.Subscription.delete(subscription_id)
        except stripe.StripeError as e:
            logger.error("Stripe cancel subscription error", error=str(e))
            raise

def get_payment_provider() -> PaymentProvider:
    if settings.PAYMENT_PROVIDER == "stripe":
        return StripeProvider()
    else:
        raise ValueError(f"Unsupported payment provider: {settings.PAYMENT_PROVIDER}")
