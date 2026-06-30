"""FastAPI application factory and entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.redis import close_redis, init_redis
from app.core.middleware import IdempotencyMiddleware, RequestContextMiddleware
from app.ws.connection_manager import hub


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    redis = await init_redis()  # warm the pool, fail fast if Redis is unreachable
    await hub.start(redis)  # start the WebSocket pub/sub fan-out
    yield
    await hub.stop()
    await close_redis()


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    # Inner: idempotency replay-protection; Outer: request id + security headers.
    app.add_middleware(IdempotencyMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)

    @app.get("/health", tags=["meta"], summary="Liveness probe")
    async def health() -> dict[str, str]:
        return {"status": "ok", "environment": settings.ENVIRONMENT}

    return app


app = create_app()
