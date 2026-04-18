import asyncio
from celery import shared_task
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from src.core.config import settings
from src.application.subscription_service import SubscriptionService
from src.infrastructure.payment_provider import get_payment_provider
from src.infrastructure.remnawave_client import RemnawaveClient
from src.infrastructure.repositories.subscription_repository import SubscriptionRepository
from src.db.models import Subscription
import structlog

logger = structlog.get_logger()

@shared_task
def renew_expiring_subscriptions():
    """Check and renew subscriptions that are due for renewal"""
    async def _run():
        engine = create_async_engine(settings.DATABASE_URL)
        async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

        async with async_session() as session:
            repo = SubscriptionRepository(session)
            # Find active subscriptions with auto_renew=True and end_date within next day
            # Simplified: fetch all active with auto_renew and check in Python
            subs = await repo.list(status="active", auto_renew=True)
            payment_provider = get_payment_provider()
            remnawave = RemnawaveClient()
            service = SubscriptionService(session, payment_provider, remnawave)

            for sub in subs:
                success = await service.renew_subscription(sub.id)
                if success:
                    logger.info("Subscription renewed", subscription_id=sub.id)
                else:
                    logger.info("Subscription not renewed", subscription_id=sub.id)

        await engine.dispose()

    asyncio.run(_run())
