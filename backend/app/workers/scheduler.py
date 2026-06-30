"""Standalone worker that periodically dispatches due scheduled rides.

Run with:  python -m app.workers.scheduler
In production this runs as its own process/container alongside the API.
"""
from __future__ import annotations

import asyncio
import logging

from app.core.database import AsyncSessionLocal
from app.core.logging import configure_logging
from app.core.redis import close_redis, init_redis
from app.services.scheduler_service import SchedulerService

logger = logging.getLogger("app.workers.scheduler")
POLL_SECONDS = 15


async def run() -> None:
    configure_logging()
    redis = await init_redis()
    try:
        while True:
            try:
                async with AsyncSessionLocal() as session:
                    n = await SchedulerService(session, redis).dispatch_due()
                    if n:
                        logger.info("Dispatched %d scheduled ride(s)", n)
            except Exception:  # pragma: no cover
                logger.exception("scheduler tick failed")
            await asyncio.sleep(POLL_SECONDS)
    finally:
        await close_redis()


if __name__ == "__main__":
    asyncio.run(run())
