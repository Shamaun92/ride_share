"""Refresh-token lifecycle backed by Redis.

We store each issued refresh token's jti in Redis with a TTL equal to the
token's lifetime. Logout / rotation deletes the jti. A refresh token is only
honored if its jti is still present -> instant revocation, no DB writes on the
hot path.
"""
from __future__ import annotations

import uuid

from redis.asyncio import Redis

from app.core.config import settings

_REFRESH_PREFIX = "refresh_jti:"


def _key(user_id: str | uuid.UUID, jti: str) -> str:
    return f"{_REFRESH_PREFIX}{user_id}:{jti}"


class TokenService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis

    async def store_refresh(self, user_id: str | uuid.UUID, jti: str) -> None:
        ttl = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
        await self.redis.set(_key(user_id, jti), "1", ex=ttl)

    async def is_valid(self, user_id: str | uuid.UUID, jti: str) -> bool:
        return await self.redis.exists(_key(user_id, jti)) == 1

    async def revoke(self, user_id: str | uuid.UUID, jti: str) -> None:
        await self.redis.delete(_key(user_id, jti))

    async def revoke_all(self, user_id: str | uuid.UUID) -> None:
        """Used on password change / forced logout-everywhere."""
        pattern = f"{_REFRESH_PREFIX}{user_id}:*"
        async for key in self.redis.scan_iter(match=pattern):
            await self.redis.delete(key)
