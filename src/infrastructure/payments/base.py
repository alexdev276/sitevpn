from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(slots=True)
class CheckoutSession:
    payment_id: str
    checkout_url: str
    subscription_id: str | None = None
    raw: dict[str, Any] | None = None


@dataclass(slots=True)
class WebhookEvent:
    event_type: str
    provider_payment_id: str
    status: str
    metadata: dict[str, Any]
    provider_subscription_id: str | None = None


class PaymentProvider(ABC):
    @abstractmethod
    async def create_checkout_session(
        self,
        *,
        amount: Decimal,
        currency: str,
        description: str,
        metadata: dict[str, str],
        recurring_interval: str,
    ) -> CheckoutSession:
        raise NotImplementedError

    @abstractmethod
    async def parse_webhook(self, payload: bytes, signature: str | None) -> WebhookEvent:
        raise NotImplementedError

    @abstractmethod
    async def cancel_subscription(self, provider_subscription_id: str) -> None:
        raise NotImplementedError

