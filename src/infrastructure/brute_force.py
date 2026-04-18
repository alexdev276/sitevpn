from datetime import timedelta
from src.infrastructure.redis_client import get_redis
from src.core.config import settings

class BruteForceProtector:
    def __init__(self):
        self.max_attempts = settings.MAX_LOGIN_ATTEMPTS
        self.block_time = settings.LOGIN_BLOCK_TIME_MINUTES * 60

    async def _get_redis(self):
        return await anext(get_redis())

    async def is_blocked(self, identifier: str) -> bool:
        redis = await self._get_redis()
        key = f"brute_force:block:{identifier}"
        return await redis.exists(key) > 0

    async def record_failure(self, identifier: str):
        redis = await self._get_redis()
        attempts_key = f"brute_force:attempts:{identifier}"
        attempts = await redis.incr(attempts_key)
        if attempts == 1:
            await redis.expire(attempts_key, self.block_time)
        if attempts >= self.max_attempts:
            block_key = f"brute_force:block:{identifier}"
            await redis.set(block_key, "1", ex=self.block_time)
            await redis.delete(attempts_key)

    async def reset(self, identifier: str):
        redis = await self._get_redis()
        await redis.delete(f"brute_force:attempts:{identifier}")
        await redis.delete(f"brute_force:block:{identifier}")
