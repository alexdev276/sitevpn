import json
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from src.application.payment_service import PaymentService
from src.db.models import Payment, Subscription, Tariff, User
from src.domain.enums import PaymentProviderType, PaymentStatus, SubscriptionStatus, TariffPeriod, UserRole
from src.infrastructure.payments.base import WebhookEvent


@pytest.mark.asyncio
async def test_handle_webhook_activates_subscription(db_session, settings):
    user = User(email="pay@example.com", password_hash="hash", role=UserRole.USER, is_email_confirmed=True)
    tariff = Tariff(
        name="Yearly",
        period=TariffPeriod.YEARLY,
        price=Decimal("99.00"),
        duration_days=365,
        traffic_limit_bytes=2048,
    )
    db_session.add_all([user, tariff])
    await db_session.flush()
    subscription = Subscription(
        user_id=user.id,
        tariff_id=tariff.id,
        status=SubscriptionStatus.PENDING,
        starts_at=user.created_at,
        ends_at=user.created_at,
    )
    db_session.add(subscription)
    await db_session.flush()
    payment = Payment(
        user_id=user.id,
        subscription_id=subscription.id,
        amount=Decimal("99.00"),
        currency="USD",
        provider=PaymentProviderType.STRIPE,
        status=PaymentStatus.PENDING,
        provider_payment_id="cs_123",
        provider_payload={},
    )
    db_session.add(payment)
    await db_session.commit()

    provider = AsyncMock()
    provider.parse_webhook.return_value = WebhookEvent(
        event_type="checkout.session.completed",
        provider_payment_id="cs_123",
        status="paid",
        metadata={"subscription_id": str(subscription.id)},
    )

    service = PaymentService(db_session, settings, provider)
    service.vpn_service.ensure_vpn_user = AsyncMock()
    await service.handle_webhook(json.dumps({"ok": True}).encode(), "signature")

    refreshed_payment = await db_session.get(Payment, payment.id)
    refreshed_subscription = await db_session.get(Subscription, subscription.id)
    assert refreshed_payment.status == PaymentStatus.SUCCEEDED
    assert refreshed_subscription.status == SubscriptionStatus.ACTIVE
