"""Test fixtures: in-memory SQLite DB + fake Redis, app dependency overrides."""
from __future__ import annotations

from collections.abc import AsyncGenerator

import fakeredis.aioredis
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_current_user  # noqa: F401  (ensures import graph loads)
from app.core.database import get_db
from app.core.redis import get_redis
from app.main import app
from app.models.base import Base


@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def redis_conn():
    fake = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield fake
    await fake.aclose()


@pytest_asyncio.fixture
async def client(
    db_session: AsyncSession, redis_conn
) -> AsyncGenerator[AsyncClient, None]:
    async def _get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    async def _get_redis():
        return redis_conn

    app.dependency_overrides[get_db] = _get_db
    app.dependency_overrides[get_redis] = _get_redis

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
