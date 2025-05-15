# app/utils/redis_client.py
import redis
from app.config.setting import settings


class RedisClient:
    def __init__(self):
        self.redis_client = None

    async def connect(self):
        # Connect to Redis using the URL from settings
        self.redis_client = redis.Redis.from_url(settings.REDIS_URL)
        return self.redis_client

    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()


# Initialize a global Redis client instance
redis_client = RedisClient()
