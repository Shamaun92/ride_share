"""HTTP middleware: request context (correlation id + security headers) and
idempotency for unsafe, money-touching requests.
"""
from __future__ import annotations

import json
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core import redis as redis_module
from app.core.audit import logger as audit_logger  # noqa: F401  (ensures logger exists)
from app.core.config import settings

REQUEST_ID_HEADER = "X-Request-ID"
IDEMPOTENCY_HEADER = "idempotency-key"
REPLAY_HEADER = "X-Idempotent-Replay"

_SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "0",
}


class RequestContextMiddleware(BaseHTTPMiddleware):
    """Attach a correlation id to every request/response and set security headers."""

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get(REQUEST_ID_HEADER) or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        if settings.SECURITY_HEADERS_ENABLED:
            for k, v in _SECURITY_HEADERS.items():
                response.headers.setdefault(k, v)
        return response


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Replay-protect POST/PATCH requests carrying an Idempotency-Key.

    The first successful (2xx) response for a (caller, method, path, key) tuple
    is cached in Redis; subsequent identical requests return the stored response
    instead of re-executing — preventing double charges on client retries.
    No-ops when Redis is not initialised (e.g. most unit tests).
    """

    async def dispatch(self, request: Request, call_next):
        key = request.headers.get(IDEMPOTENCY_HEADER)
        if not key or request.method not in ("POST", "PATCH"):
            return await call_next(request)

        redis = redis_module._redis
        if redis is None:
            return await call_next(request)

        # Scope by the auth token so keys can't collide across callers.
        auth = request.headers.get("authorization", "")
        scope = str(abs(hash(auth)) % (10**12))
        rkey = f"idem:{scope}:{request.method}:{request.url.path}:{key}"

        try:
            cached = await redis.get(rkey)
        except Exception:  # pragma: no cover - fail open
            cached = None
        if cached:
            data = json.loads(cached)
            return Response(
                content=data["body"],
                status_code=data["status"],
                media_type=data.get("media_type", "application/json"),
                headers={REPLAY_HEADER: "true"},
            )

        response = await call_next(request)
        body = b"".join([chunk async for chunk in response.body_iterator])

        if 200 <= response.status_code < 300:
            try:
                await redis.set(
                    rkey,
                    json.dumps(
                        {
                            "status": response.status_code,
                            "media_type": response.media_type,
                            "body": body.decode("utf-8", "ignore"),
                        }
                    ),
                    ex=settings.IDEMPOTENCY_TTL_SECONDS,
                )
            except Exception:  # pragma: no cover - fail open
                pass

        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )
