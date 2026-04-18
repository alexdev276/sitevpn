from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest

from src.db.models import Tariff
from src.domain.enums import TariffPeriod
from src.infrastructure.payments.base import CheckoutSession


@pytest.mark.asyncio
async def test_register_and_create_payment_flow(client, db_session, redis_mock):
    tariff = Tariff(
        name="Monthly",
        period=TariffPeriod.MONTHLY,
        price=Decimal("10.00"),
        duration_days=30,
        traffic_limit_bytes=1024,
    )
    db_session.add(tariff)
    await db_session.commit()

    register_response = await client.post(
        "/api/v1/auth/register",
        json={"email": "flow@example.com", "password": "strong-password"},
    )
    assert register_response.status_code == 200

    code = await redis_mock.get("verify:flow@example.com")
    confirm_response = await client.post(
        "/api/v1/auth/confirm-email",
        json={"email": "flow@example.com", "code": code},
    )
    assert confirm_response.status_code == 200

    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "flow@example.com", "password": "strong-password"},
    )
    assert login_response.status_code == 200
    access_token = login_response.json()["access_token"]

    with patch("src.core.dependencies.StripePaymentProvider") as provider_cls:
        provider = AsyncMock()
        provider.create_checkout_session.return_value = CheckoutSession(
            payment_id="cs_test",
            checkout_url="https://checkout.stripe.test",
            subscription_id="sub_test",
            raw={"id": "cs_test"},
        )
        provider_cls.return_value = provider

        payment_response = await client.post(
            "/api/v1/payments",
            json={"tariff_id": str(tariff.id)},
            headers={"Authorization": f"Bearer {access_token}"},
        )

    assert payment_response.status_code == 200
    assert payment_response.json()["checkout_url"] == "https://checkout.stripe.test"
