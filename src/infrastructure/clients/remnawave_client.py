from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from src.core.config import Settings


class RemnawaveClient:
    """
    Thin adapter over the official remnawave SDK.
    We keep dynamic resolution here so the application layer does not depend
    on potential naming changes between SDK versions.
    """

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._sdk = self._build_sdk()

    def _build_sdk(self) -> Any:
        import remnawave

        candidates = [
            getattr(remnawave, "Remnawave", None),
            getattr(remnawave, "Client", None),
            getattr(remnawave, "RemnawaveClient", None),
        ]
        client_cls = next((candidate for candidate in candidates if candidate is not None), None)
        if client_cls is None:
            raise RuntimeError("Unsupported remnawave SDK version: client class not found")

        try:
            return client_cls(
                base_url=self.settings.remnawave_base_url,
                api_key=self.settings.remnawave_api_key,
            )
        except TypeError:
            return client_cls(
                self.settings.remnawave_base_url,
                self.settings.remnawave_api_key,
            )

    async def create_user(
        self,
        *,
        username: str,
        expire_at: datetime,
        traffic_limit_bytes: int,
    ) -> dict[str, Any]:
        payload = {
            "username": username,
            "expireAt": expire_at.isoformat(),
            "trafficLimitBytes": traffic_limit_bytes,
            "squadId": self.settings.remnawave_internal_squad_id,
        }
        return await asyncio.to_thread(self._call_sdk, "create_user", payload)

    async def block_user(self, remnawave_user_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._call_sdk, "block_user", {"userId": remnawave_user_id})

    async def extend_user(
        self,
        remnawave_user_id: str,
        expire_at: datetime,
        traffic_limit_bytes: int,
    ) -> dict[str, Any]:
        payload = {
            "userId": remnawave_user_id,
            "expireAt": expire_at.isoformat(),
            "trafficLimitBytes": traffic_limit_bytes,
        }
        return await asyncio.to_thread(self._call_sdk, "extend_user", payload)

    async def delete_user(self, remnawave_user_id: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._call_sdk, "delete_user", {"userId": remnawave_user_id})

    def _call_sdk(self, method_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        users_api = getattr(self._sdk, "users", self._sdk)
        method = getattr(users_api, method_name)
        try:
            result = method(**payload)
        except TypeError:
            result = method(payload)
        if hasattr(result, "model_dump"):
            return result.model_dump()
        if isinstance(result, dict):
            return result
        return {"result": str(result)}

