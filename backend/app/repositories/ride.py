"""Ride and RideOffer data access.

The `claim` method is the concurrency heart of dispatch: a conditional UPDATE
that only succeeds if the ride is still REQUESTED, so exactly one driver wins a
race to accept. Driver state-changing reads use SELECT ... FOR UPDATE to
serialize transitions on the same ride.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.driver import DriverProfile
from app.core.geo import bounding_box
from app.models.enums import OfferStatus, RideStatus
from app.models.ride import Ride
from app.models.ride_offer import RideOffer
from app.repositories.base import BaseRepository
from app.services.ride_state import ACTIVE_STATUSES


class RideRepository(BaseRepository[Ride]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Ride, session)

    async def get_detail(self, ride_id: uuid.UUID) -> Ride | None:
        """Load a ride with the assigned driver, their user, and vehicles.

        `populate_existing` refreshes any identity-mapped instance from this
        query — essential after the Core-level `claim` UPDATE, whose changes
        bypass the ORM unit of work.
        """
        result = await self.session.execute(
            select(Ride)
            .where(Ride.id == ride_id)
            .options(
                selectinload(Ride.driver).selectinload(DriverProfile.user),
                selectinload(Ride.driver).selectinload(DriverProfile.vehicles),
            )
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def get_for_update(self, ride_id: uuid.UUID) -> Ride | None:
        """Row-locked fetch (Postgres) to serialize state transitions."""
        result = await self.session.execute(
            select(Ride).where(Ride.id == ride_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_active_for_rider(self, rider_id: uuid.UUID) -> Ride | None:
        result = await self.session.execute(
            select(Ride).where(
                Ride.rider_id == rider_id,
                Ride.status.in_(ACTIVE_STATUSES),
            )
        )
        return result.scalars().first()

    async def get_active_for_driver(self, driver_id: uuid.UUID) -> Ride | None:
        result = await self.session.execute(
            select(Ride).where(
                Ride.driver_id == driver_id,
                Ride.status.in_(ACTIVE_STATUSES),
            )
        )
        return result.scalars().first()

    async def list_for_rider(
        self, rider_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[Ride]:
        result = await self.session.execute(
            select(Ride)
            .where(Ride.rider_id == rider_id)
            .order_by(Ride.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_for_driver(
        self, driver_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[Ride]:
        result = await self.session.execute(
            select(Ride)
            .where(Ride.driver_id == driver_id)
            .order_by(Ride.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        return list(result.scalars().all())

    async def list_due_scheduled(
        self, now: datetime, *, limit: int = 100
    ) -> list[Ride]:
        result = await self.session.execute(
            select(Ride)
            .where(
                Ride.status == RideStatus.SCHEDULED,
                Ride.scheduled_for.is_not(None),
                Ride.scheduled_for <= now,
            )
            .order_by(Ride.scheduled_for.asc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def count_open_requests_near(
        self, lat: float, lng: float, radius_km: float
    ) -> int:
        min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius_km)
        result = await self.session.execute(
            select(func.count())
            .select_from(Ride)
            .where(
                Ride.status == RideStatus.REQUESTED,
                Ride.pickup_lat >= min_lat,
                Ride.pickup_lat <= max_lat,
                Ride.pickup_lng >= min_lng,
                Ride.pickup_lng <= max_lng,
            )
        )
        return int(result.scalar_one())

    async def claim(
        self, ride_id: uuid.UUID, driver_id: uuid.UUID, accepted_at: datetime
    ) -> bool:
        """Atomically transition REQUESTED -> ACCEPTED for exactly one driver.
        Returns True if this caller won the claim.
        """
        result = await self.session.execute(
            update(Ride)
            .where(Ride.id == ride_id, Ride.status == RideStatus.REQUESTED)
            .values(
                status=RideStatus.ACCEPTED,
                driver_id=driver_id,
                accepted_at=accepted_at,
            )
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1


class RideOfferRepository(BaseRepository[RideOffer]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(RideOffer, session)

    async def get_for_ride_and_driver(
        self, ride_id: uuid.UUID, driver_id: uuid.UUID
    ) -> RideOffer | None:
        result = await self.session.execute(
            select(RideOffer).where(
                RideOffer.ride_id == ride_id,
                RideOffer.driver_id == driver_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_pending_for_driver(
        self, driver_id: uuid.UUID, now: datetime
    ) -> list[RideOffer]:
        result = await self.session.execute(
            select(RideOffer)
            .where(
                RideOffer.driver_id == driver_id,
                RideOffer.status == OfferStatus.PENDING,
                RideOffer.expires_at > now,
            )
            .order_by(RideOffer.distance_km.asc())
        )
        return list(result.scalars().all())

    async def expire_other_pending(
        self, ride_id: uuid.UUID, except_offer_id: uuid.UUID
    ) -> None:
        await self.session.execute(
            update(RideOffer)
            .where(
                RideOffer.ride_id == ride_id,
                RideOffer.id != except_offer_id,
                RideOffer.status == OfferStatus.PENDING,
            )
            .values(status=OfferStatus.EXPIRED)
            .execution_options(synchronize_session=False)
        )

    async def expire_pending_for_ride(self, ride_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RideOffer)
            .where(
                RideOffer.ride_id == ride_id,
                RideOffer.status == OfferStatus.PENDING,
            )
            .values(status=OfferStatus.EXPIRED)
            .execution_options(synchronize_session=False)
        )

    async def expire_pending_for_driver(self, driver_id: uuid.UUID) -> None:
        await self.session.execute(
            update(RideOffer)
            .where(
                RideOffer.driver_id == driver_id,
                RideOffer.status == OfferStatus.PENDING,
            )
            .values(status=OfferStatus.EXPIRED)
            .execution_options(synchronize_session=False)
        )
