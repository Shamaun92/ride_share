"""Driver profile data access, including nearby-driver dispatch search."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.geo import bounding_box, haversine_km
from app.models.driver import DriverProfile
from app.models.enums import DriverStatus, VehicleType
from app.repositories.base import BaseRepository


class DriverRepository(BaseRepository[DriverProfile]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(DriverProfile, session)

    async def get_by_user_id(self, user_id: uuid.UUID) -> DriverProfile | None:
        result = await self.session.execute(
            select(DriverProfile)
            .where(DriverProfile.user_id == user_id)
            .options(selectinload(DriverProfile.vehicles))
        )
        return result.scalar_one_or_none()

    async def get_with_vehicles(
        self, driver_id: uuid.UUID
    ) -> DriverProfile | None:
        result = await self.session.execute(
            select(DriverProfile)
            .where(DriverProfile.id == driver_id)
            .options(selectinload(DriverProfile.vehicles))
        )
        return result.scalar_one_or_none()

    async def get_many_with_vehicles(
        self, driver_ids: list[uuid.UUID]
    ) -> list[DriverProfile]:
        if not driver_ids:
            return []
        result = await self.session.execute(
            select(DriverProfile)
            .where(DriverProfile.id.in_(driver_ids))
            .options(selectinload(DriverProfile.vehicles))
        )
        return list(result.scalars().all())

    async def find_nearby_available(
        self,
        lat: float,
        lng: float,
        radius_km: float,
        vehicle_type: VehicleType,
        limit: int,
    ) -> list[tuple[DriverProfile, float]]:
        """ONLINE drivers within `radius_km` that operate a matching active
        vehicle, ordered nearest-first. Returns (driver, distance_km) pairs.

        Bounding box is the index-friendly SQL prefilter; haversine refines in
        Python. At scale this moves to Redis GEO (Phase 3) / PostGIS.
        """
        min_lat, max_lat, min_lng, max_lng = bounding_box(lat, lng, radius_km)
        stmt = (
            select(DriverProfile)
            .where(
                DriverProfile.status == DriverStatus.ONLINE,
                DriverProfile.current_lat.is_not(None),
                DriverProfile.current_lng.is_not(None),
                DriverProfile.current_lat >= min_lat,
                DriverProfile.current_lat <= max_lat,
                DriverProfile.current_lng >= min_lng,
                DriverProfile.current_lng <= max_lng,
            )
            .options(selectinload(DriverProfile.vehicles))
        )
        result = await self.session.execute(stmt)
        candidates = result.scalars().all()

        scored: list[tuple[DriverProfile, float]] = []
        for driver in candidates:
            has_vehicle = any(
                v.is_active and v.vehicle_type == vehicle_type
                for v in driver.vehicles
            )
            if not has_vehicle:
                continue
            dist = haversine_km(
                lat, lng, driver.current_lat, driver.current_lng  # type: ignore[arg-type]
            )
            if dist <= radius_km:
                scored.append((driver, dist))

        scored.sort(key=lambda pair: pair[1])
        return scored[:limit]
