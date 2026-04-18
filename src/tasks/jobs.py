from __future__ import annotations

import asyncio

import structlog
from sqlalchemy import select

from src.application.payment_service import PaymentService
from src.application.vpn_service import VpnService
from src.core.config import get_settings
from src.core.security import utcnow
from src.db.models import Subscription, VpnUser
from src.db.session import AsyncSessionLocal
from src.domain.enums import SubscriptionStatus
from src.infrastructure.payments.stripe_provider import StripePaymentProvider
from src.tasks.celery_app import celery_app


logger = structlog.get_logger(__name__)


@celery_app.task(name="src.tasks.jobs.send_email_code")
def send_email_code(email: str, code: str, purpose: str) -> None:
    logger.info("email_task", email=email, code=code, purpose=purpose)


@celery_app.task(name="src.tasks.jobs.renew_expired_subscriptions")
def renew_expired_subscriptions() -> None:
    asyncio.run(_renew_expired_subscriptions())


async def _renew_expired_subscriptions() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Subscription).where(
                Subscription.auto_renew.is_(True),
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.ends_at <= utcnow(),
            )
        )
        subscriptions = list(result.scalars().all())
        payment_service = PaymentService(session, settings, StripePaymentProvider(settings))
        for subscription in subscriptions:
            try:
                await payment_service.create_payment(subscription.user_id, subscription.tariff_id)
            except Exception as exc:  # pragma: no cover
                logger.exception(
                    "subscription_renewal_failed",
                    subscription_id=str(subscription.id),
                    error=str(exc),
                )


@celery_app.task(name="src.tasks.jobs.sync_remnawave_usage")
def sync_remnawave_usage() -> None:
    asyncio.run(_sync_remnawave_usage())


async def _sync_remnawave_usage() -> None:
    settings = get_settings()
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(VpnUser))
        vpn_service = VpnService(session, settings)
        for vpn_user in result.scalars().all():
            # Placeholder for a future stats sync method if SDK exposes usage endpoints.
            logger.info("sync_vpn_user", vpn_user_id=str(vpn_user.id), username=vpn_user.username)
        await session.commit()

