from redis.asyncio import Redis, ConnectionPool
from src.core.config import settings

class RedisClient:
    def __init__(self):
        self.pool: ConnectionPool = None
        self.client: Redis = None

    async def initialize(self):
        self.pool = ConnectionPool.from_url(
            settings.REDIS_URL,
            max_connections=settings.REDIS_MAX_CONNECTIONS,
            decode_responses=True,
        )
        self.client = Redis(connection_pool=self.pool)

    async def close(self):
        if self.client:
            await self.client.close()
        if self.pool:
            await self.pool.disconnect()

    async def get(self, key: str):
        return await self.client.get(key)

    async def set(self, key: str, value: str, ex: int = None):
        return await self.client.set(key, value, ex=ex)

    async def delete(self, key: str):
        return await self.client.delete(key)

    async def incr(self, key: str):
        return await self.client.incr(key)

    async def expire(self, key: str, seconds: int):
        return await self.client.expire(key, seconds)

    async def keys(self, pattern: str):
        return await self.client.keys(pattern)

redis_client = RedisClient()

async def get_redis() -> Redis:
    return redis_client.client
