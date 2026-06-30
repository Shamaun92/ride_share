"""Redis-backed rate limiting dependencies.

A fixed-window counter (INCR + EXPIRE) keyed per user or per client IP. Limits
are read from settings at call time so they can be tuned (and overridden in
tests) without re-importing. Fail-open: if Redis errors, the request proceeds.
"""
from __future__ import annotations

from fastapi import Depends, Request

from app.api.deps import CurrentUser, RedisDep
from app.core.config import settings
from app.core.exceptions import RateLimitError


async def _hit(redis, key: str, limit: int, window: int) -> None:
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window)
    except Exception:  # pragma: no cover - fail open on limiter failure
        return
    if count > limit:
        raise RateLimitError("Too many requests; please slow down")


def user_rate_limit(limit_attr: str = "RATE_LIMIT_DEFAULT_PER_MIN", window: int = 60):
    """Per-user limiter for authenticated, sensitive mutations."""

    async def dependency(
        request: Request, redis: RedisDep, current_user: CurrentUser
    ) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        limit = getattr(settings, limit_attr)
        key = f"rl:user:{current_user.id}:{request.url.path}:{window}"
        await _hit(redis, key, limit, window)

    return Depends(dependency)


def ip_rate_limit(limit_attr: str = "RATE_LIMIT_AUTH_PER_MIN", window: int = 60):
    """Per-IP limiter for unauthenticated endpoints (auth)."""

    async def dependency(request: Request, redis: RedisDep) -> None:
        if not settings.RATE_LIMIT_ENABLED:
            return
        limit = getattr(settings, limit_attr)
        client_ip = request.client.host if request.client else "anon"
        key = f"rl:ip:{client_ip}:{request.url.path}:{window}"
        await _hit(redis, key, limit, window)

    return Depends(dependency)
