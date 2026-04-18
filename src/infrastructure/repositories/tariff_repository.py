from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Tariff


class TariffRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, tariff_id: UUID) -> Tariff | None:
        return await self.session.get(Tariff, tariff_id)

    async def list_active(self) -> list[Tariff]:
        result = await self.session.execute(select(Tariff).where(Tariff.is_active.is_(True)))
        return list(result.scalars().all())

    async def create(self, **payload) -> Tariff:
        tariff = Tariff(**payload)
        self.session.add(tariff)
        await self.session.flush()
        return tariff

