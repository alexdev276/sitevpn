from sqlalchemy.ext.asyncio import AsyncSession
from src.db.models import User
from src.infrastructure.repositories.base import BaseRepository

class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_email(self, email: str) -> User | None:
        return await self.get_by(email=email)

    async def get_active_by_email(self, email: str) -> User | None:
        return await self.get_by(email=email, is_active=True)

    async def update_password(self, user_id: int, hashed_password: str) -> None:
        await self.update(user_id, hashed_password=hashed_password)

    async def verify_email(self, user_id: int) -> None:
        await self.update(user_id, is_verified=True)
