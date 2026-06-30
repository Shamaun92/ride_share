"""Due-ride dispatcher for scheduled rides.

`dispatch_due` finds SCHEDULED rides whose time has arrived and dispatches each
through the normal offer flow. Intended to be run periodically by a worker
(see app/workers/scheduler.py) or triggered by an admin/cron endpoint.
"""
from __future__ import annotations

from datetime import datetime, timezone

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.ride import RideRepository
from app.services.ride_service import RideService


class SchedulerService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.rides = RideRepository(session)
        self.ride_service = RideService(session, redis)

    async def dispatch_due(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        due = await self.rides.list_due_scheduled(now)
        dispatched = 0
        for ride in due:
            await self.ride_service.dispatch_scheduled_ride(ride)
            dispatched += 1
        return dispatched
