from __future__ import annotations

import hmac
import json
from decimal import Decimal
from hashlib import sha256

import httpx

from src.core.config import Settings
from src.core.exceptions import AppException
from src.infrastructure.payments.base import CheckoutSession, PaymentProvider, WebhookEvent


class StripePaymentProvider(PaymentProvider):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def create_checkout_session(
        self,
        *,
        amount: Decimal,
        currency: str,
        description: str,
        metadata: dict[str, str],
        recurring_interval: str,
    ) -> CheckoutSession:
        async with httpx.AsyncClient(
            base_url=self.settings.stripe_api_base,
            auth=(self.settings.stripe_secret_key, ""),
            timeout=20.0,
        ) as client:
            payload = {
                "mode": "subscription",
                "success_url": self.settings.stripe_success_url,
                "cancel_url": self.settings.stripe_cancel_url,
                "line_items[0][price_data][currency]": currency.lower(),
                "line_items[0][price_data][product_data][name]": description,
                "line_items[0][price_data][recurring][interval]": recurring_interval,
                "line_items[0][price_data][unit_amount]": str(int(amount * 100)),
                "line_items[0][quantity]": "1",
            }
            for key, value in metadata.items():
                payload[f"metadata[{key}]"] = value
            response = await client.post("/v1/checkout/sessions", data=payload)
            response.raise_for_status()
            data = response.json()
            return CheckoutSession(
                payment_id=data["id"],
                checkout_url=data["url"],
                subscription_id=data.get("subscription"),
                raw=data,
            )

    async def parse_webhook(self, payload: bytes, signature: str | None) -> WebhookEvent:
        if not signature:
            raise AppException("Missing Stripe signature", 400, "missing_signature")

        expected = hmac.new(
            self.settings.stripe_webhook_secret.encode(),
            payload,
            sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise AppException("Invalid Stripe signature", 400, "invalid_signature")

        data = json.loads(payload.decode("utf-8"))
        obj = data["data"]["object"]
        metadata = obj.get("metadata", {})
        return WebhookEvent(
            event_type=data["type"],
            provider_payment_id=obj["id"],
            status=obj.get("payment_status") or obj.get("status", "unknown"),
            metadata=metadata,
            provider_subscription_id=obj.get("subscription"),
        )

    async def cancel_subscription(self, provider_subscription_id: str) -> None:
        async with httpx.AsyncClient(
            base_url=self.settings.stripe_api_base,
            auth=(self.settings.stripe_secret_key, ""),
            timeout=20.0,
        ) as client:
            response = await client.delete(f"/v1/subscriptions/{provider_subscription_id}")
            response.raise_for_status()

