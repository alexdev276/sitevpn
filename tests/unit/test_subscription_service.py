from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from src.application.subscription_service import SubscriptionService
from src.db.models import Tariff, User
from src.domain.enums import SubscriptionStatus, TariffPeriod, UserRole


@pytest.mark.asyncio
async def test_create_pending_subscription(db_session):
    user = User(
        email="user@example.com",
        password_hash="hash",
        role=UserRole.USER,
        is_email_confirmed=True,
    )
    tariff = Tariff(
        name="Monthly",
        period=TariffPeriod.MONTHLY,
        price=Decimal("9.99"),
        duration_days=30,
        traffic_limit_bytes=1024,
    )
    db_session.add_all([user, tariff])
    await db_session.commit()

    service = SubscriptionService(db_session)
    subscription = await service.create_pending_subscription(user.id, tariff.id)

    assert subscription.status == SubscriptionStatus.PENDING
    assert subscription.ends_at > datetime.now(UTC)

