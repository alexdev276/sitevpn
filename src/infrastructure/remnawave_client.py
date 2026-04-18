from typing import Optional, Dict, Any
from datetime import datetime
import remnawave
from src.core.config import settings
from src.core.exceptions import RemnawaveError
import structlog

logger = structlog.get_logger()

class RemnawaveClient:
    def __init__(self):
        self.client = remnawave.RemnaWaveAPI(
            base_url=str(settings.REMNAWAVE_API_URL),
            api_key=settings.REMNAWAVE_API_KEY,
        )
        self.squad_id = settings.REMNAWAVE_SQUAD_ID

    async def create_user(
        self,
        username: str,
        expire_at: Optional[datetime] = None,
        traffic_limit_bytes: Optional[int] = None,
        telegram_id: Optional[int] = None,
        email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create VPN user in Remnawave panel"""
        try:
            payload = {
                "username": username,
                "status": "ACTIVE",
                "squadId": self.squad_id,
            }
            if expire_at:
                payload["expireAt"] = expire_at.isoformat()
            if traffic_limit_bytes:
                payload["trafficLimitBytes"] = traffic_limit_bytes
            if telegram_id:
                payload["telegramId"] = telegram_id
            if email:
                payload["email"] = email

            response = await self.client.user.create_user(payload)
            logger.info("Remnawave user created", username=username, uuid=response.get("uuid"))
            return response
        except Exception as e:
            logger.error("Failed to create Remnawave user", error=str(e))
            raise RemnawaveError(f"Failed to create VPN user: {str(e)}")

    async def get_user(self, uuid: str) -> Dict[str, Any]:
        try:
            return await self.client.user.get_user(uuid)
        except Exception as e:
            logger.error("Failed to get Remnawave user", uuid=uuid, error=str(e))
            raise RemnawaveError(f"Failed to get VPN user: {str(e)}")

    async def update_user(
        self,
        uuid: str,
        expire_at: Optional[datetime] = None,
        traffic_limit_bytes: Optional[int] = None,
        status: Optional[str] = None,
    ) -> Dict[str, Any]:
        try:
            payload = {}
            if expire_at is not None:
                payload["expireAt"] = expire_at.isoformat() if expire_at else None
            if traffic_limit_bytes is not None:
                payload["trafficLimitBytes"] = traffic_limit_bytes
            if status is not None:
                payload["status"] = status

            response = await self.client.user.update_user(uuid, payload)
            logger.info("Remnawave user updated", uuid=uuid)
            return response
        except Exception as e:
            logger.error("Failed to update Remnawave user", uuid=uuid, error=str(e))
            raise RemnawaveError(f"Failed to update VPN user: {str(e)}")

    async def block_user(self, uuid: str) -> Dict[str, Any]:
        return await self.update_user(uuid, status="DISABLED")

    async def unblock_user(self, uuid: str) -> Dict[str, Any]:
        return await self.update_user(uuid, status="ACTIVE")

    async def delete_user(self, uuid: str) -> bool:
        try:
            await self.client.user.delete_user(uuid)
            logger.info("Remnawave user deleted", uuid=uuid)
            return True
        except Exception as e:
            logger.error("Failed to delete Remnawave user", uuid=uuid, error=str(e))
            raise RemnawaveError(f"Failed to delete VPN user: {str(e)}")

    async def get_user_stats(self, uuid: str) -> Dict[str, Any]:
        try:
            # Assume get_user returns usage stats
            user = await self.get_user(uuid)
            return {
                "used_traffic_bytes": user.get("usedTrafficBytes", 0),
                "total_traffic_bytes": user.get("trafficLimitBytes", 0),
                "expire_at": user.get("expireAt"),
                "is_active": user.get("status") == "ACTIVE",
            }
        except Exception as e:
            logger.error("Failed to get user stats", uuid=uuid, error=str(e))
            raise RemnawaveError(f"Failed to get VPN stats: {str(e)}")
