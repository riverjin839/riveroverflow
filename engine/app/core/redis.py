import redis.asyncio as aioredis
from .config import settings

_redis: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


async def publish(channel: str, message: str) -> None:
    r = await get_redis()
    await r.publish(channel, message)


# Redis channel names (must match gateway/internal/ws/hub.go)
CHANNEL_TRADES = "riveroverflow:trades"
CHANNEL_MARKET = "riveroverflow:market"
CHANNEL_PORTFOLIO = "riveroverflow:portfolio"
