from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import Settings
from src.core.exceptions import NotFoundException
from src.db.models import Subscription
from src.infrastructure.clients.remnawave_client import RemnawaveClient
from src.infrastructure.repositories.tariff_repository import TariffRepository
from src.infrastructure.repositories.user_repository import UserRepository
from src.infrastructure.repositories.vpn_repository import VpnRepository


class VpnService:
    def __init__(self, session: AsyncSession, settings: Settings) -> None:
        self.session = session
        self.settings = settings
        self._client: RemnawaveClient | None = None
        self.users = UserRepository(session)
        self.vpn_users = VpnRepository(session)
        self.tariffs = TariffRepository(session)

    @property
    def client(self) -> RemnawaveClient:
        if self._client is None:
            self._client = RemnawaveClient(self.settings)
        return self._client

    async def ensure_vpn_user(self, user_id: UUID, subscription: Subscription) -> None:
        user = await self.users.get_by_id(user_id)
        tariff = await self.tariffs.get_by_id(subscription.tariff_id)
        if not user:
            raise NotFoundException("User not found")
        if not tariff:
            raise NotFoundException("Tariff not found")
        vpn_user = await self.vpn_users.get_by_user_id(user_id)
        if vpn_user:
            updated = await self.client.extend_user(
                vpn_user.remnawave_user_id,
                subscription.ends_at,
                tariff.traffic_limit_bytes,
            )
            vpn_user.expires_at = subscription.ends_at
            vpn_user.traffic_limit_bytes = tariff.traffic_limit_bytes
            vpn_user.configs = updated.get("configs", vpn_user.configs)
            await self.session.commit()
            return

        created = await self.client.create_user(
            username=user.email,
            expire_at=subscription.ends_at,
            traffic_limit_bytes=tariff.traffic_limit_bytes,
        )
        await self.vpn_users.create(
            user_id=user.id,
            remnawave_user_id=created.get("id", created.get("userId", user.email)),
            username=user.email,
            expires_at=subscription.ends_at,
            traffic_limit_bytes=tariff.traffic_limit_bytes,
            configs=created.get("configs", {}),
        )
        await self.session.commit()

    async def block_user(self, user_id: UUID) -> None:
        vpn_user = await self.vpn_users.get_by_user_id(user_id)
        if not vpn_user:
            raise NotFoundException("VPN user not found")
        await self.client.block_user(vpn_user.remnawave_user_id)
        vpn_user.status = "blocked"
        await self.session.commit()

    async def delete_user(self, user_id: UUID) -> None:
        vpn_user = await self.vpn_users.get_by_user_id(user_id)
        if not vpn_user:
            raise NotFoundException("VPN user not found")
        await self.client.delete_user(vpn_user.remnawave_user_id)
        await self.session.delete(vpn_user)
        await self.session.commit()
