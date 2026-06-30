"""Async Redis client lifecycle.

Used for refresh-token revocation lists (auth) and, in later phases, live
driver locations and pub/sub for WebSocket fan-out.
"""
from __future__ import annotations

from redis.asyncio import Redis, from_url

from app.core.config import settings

_redis: Redis | None = None


async def init_redis() -> Redis:
    global _redis
    if _redis is None:
        _redis = from_url(
            settings.REDIS_URI,
            encoding="utf-8",
            decode_responses=True,
            health_check_interval=30,
        )
    return _redis


async def get_redis() -> Redis:
    """FastAPI dependency returning the shared Redis client."""
    return await init_redis()


async def close_redis() -> None:
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None
