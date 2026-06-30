"""Driver availability and location management.

Availability changes and location updates are mirrored into Redis: an ONLINE
driver is added to the GEO set (and removed when going OFFLINE), and each
location update refreshes GEO + the last-known snapshot and is pushed live to
the rider on any active trip.
"""
from __future__ import annotations

import logging

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ConflictError, ValidationError
from app.models.driver import DriverProfile
from app.models.enums import DriverStatus
from app.repositories.ride import RideOfferRepository, RideRepository
from app.services.location_service import LocationService
from app.ws import events

logger = logging.getLogger("app.ws")


class DriverService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.rides = RideRepository(session)
        self.offers = RideOfferRepository(session)
        self.locations = LocationService(redis)

    async def set_availability(
        self, profile: DriverProfile, target: DriverStatus
    ) -> DriverProfile:
        if profile.status == DriverStatus.ON_TRIP:
            raise ConflictError("Cannot change availability during an active trip")

        if target == DriverStatus.ONLINE:
            if profile.current_lat is None or profile.current_lng is None:
                raise ValidationError("Set your location before going online")
            profile.status = DriverStatus.ONLINE
            await self.session.commit()
            await self.session.refresh(profile)
            # Enter the live proximity index.
            await self.locations.upsert(
                profile.id, profile.current_lat, profile.current_lng
            )
        else:  # OFFLINE
            profile.status = DriverStatus.OFFLINE
            await self.offers.expire_pending_for_driver(profile.id)
            await self.session.commit()
            await self.session.refresh(profile)
            await self.locations.remove(profile.id)

        return profile

    async def update_location(
        self, profile: DriverProfile, lat: float, lng: float
    ) -> DriverProfile:
        profile.current_lat = lat
        profile.current_lng = lng
        await self.session.commit()
        await self.session.refresh(profile)

        await self.locations.upsert(profile.id, lat, lng)
        await self._broadcast_to_active_ride(profile, lat, lng)
        return profile

    async def _broadcast_to_active_ride(
        self, profile: DriverProfile, lat: float, lng: float
    ) -> None:
        """If the driver is on a trip, push the position to that ride channel."""
        try:
            ride = await self.rides.get_active_for_driver(profile.id)
            if ride is None:
                return
            await events.publish_event(
                self.redis,
                ride.id,
                events.EventType.LOCATION,
                {"driver_id": str(profile.id), "lat": lat, "lng": lng},
            )
        except Exception:  # pragma: no cover - never fail the write path
            logger.exception("Failed to broadcast driver location")
