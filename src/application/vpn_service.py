import structlog
from datetime import datetime, timedelta, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from src.infrastructure.remnawave_client import RemnawaveClient
from src.infrastructure.repositories.vpn_repository import VpnUserRepository
from src.infrastructure.repositories.subscription_repository import SubscriptionRepository
from src.domain.vpn import VpnUserResponse
from src.db.models import User, Subscription, VpnUser
from src.core.exceptions import NotFoundError, ValidationError

logger = structlog.get_logger()

class VpnService:
    def __init__(
        self,
        session: AsyncSession,
        remnawave_client: RemnawaveClient,
    ):
        self.session = session
        self.remnawave = remnawave_client
        self.vpn_repo = VpnUserRepository(session)
        self.sub_repo = SubscriptionRepository(session)

    async def provision_vpn_user(self, user: User, subscription: Subscription) -> VpnUser:
        """Create or update VPN user based on subscription"""
        # Check if user already has VPN account
        vpn_user = await self.vpn_repo.get_by_user_id(user.id)

        # Prepare params
        expire_at = subscription.end_date
        traffic_limit_bytes = subscription.tariff.traffic_limit_gb * 1024 * 1024 * 1024

        if vpn_user:
            # Update existing
            await self.remnawave.update_user(
                uuid=vpn_user.remnawave_uuid,
                expire_at=expire_at,
                traffic_limit_bytes=traffic_limit_bytes,
                status="ACTIVE",
            )
            vpn_user.is_blocked = False
            await self.session.commit()
            logger.info("VPN user updated", user_id=user.id, uuid=vpn_user.remnawave_uuid)
        else:
            # Create new
            username = f"user_{user.id}"
            remnawave_user = await self.remnawave.create_user(
                username=username,
                email=user.email,
                expire_at=expire_at,
                traffic_limit_bytes=traffic_limit_bytes,
            )
            vpn_user = await self.vpn_repo.create_for_user(
                user_id=user.id,
                remnawave_uuid=remnawave_user["uuid"],
            )
            await self.session.commit()
            logger.info("VPN user created", user_id=user.id, uuid=remnawave_user["uuid"])

        return vpn_user

    async def deactivate_vpn_user(self, user_id: int):
        vpn_user = await self.vpn_repo.get_by_user_id(user_id)
        if vpn_user:
            await self.remnawave.block_user(vpn_user.remnawave_uuid)
            vpn_user.is_blocked = True
            await self.session.commit()
            logger.info("VPN user deactivated", user_id=user_id)

    async def reactivate_vpn_user(self, user_id: int):
        vpn_user = await self.vpn_repo.get_by_user_id(user_id)
        if vpn_user:
            await self.remnawave.unblock_user(vpn_user.remnawave_uuid)
            vpn_user.is_blocked = False
            await self.session.commit()
            logger.info("VPN user reactivated", user_id=user_id)

    async def get_vpn_usage(self, user_id: int) -> dict:
        vpn_user = await self.vpn_repo.get_by_user_id(user_id)
        if not vpn_user:
            raise NotFoundError("VPN user not found")

        stats = await self.remnawave.get_user_stats(vpn_user.remnawave_uuid)
        return stats

    async def get_config_link(self, user_id: int) -> str:
        vpn_user = await self.vpn_repo.get_by_user_id(user_id)
        if not vpn_user:
            raise NotFoundError("VPN user not found")
        # Generate subscription link (e.g., vless://...)
        # This depends on Remnawave panel configuration
        return f"{settings.REMNAWAVE_API_URL}/sub/{vpn_user.remnawave_uuid}"
