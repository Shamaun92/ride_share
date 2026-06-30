"""Driver-only endpoints: profile, availability, location, dispatch offers,
and trip progression. All guarded by the CurrentDriver dependency (RBAC).
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import (
    CurrentDriver,
    DBSession,
    DriverServiceDep,
    RideServiceDep,
    require_roles,
)
from app.core.exceptions import NotFoundError
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.driver import DriverRepository
from app.schemas.driver import AvailabilityUpdate, DriverProfileRead, LocationUpdate
from app.schemas.ride import RideOfferRead, RideRead

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.get(
    "/me",
    response_model=DriverProfileRead,
    summary="Get my driver profile + vehicles",
)
async def read_my_driver_profile(
    session: DBSession,
    current_user: User = Depends(require_roles(UserRole.DRIVER)),
) -> DriverProfileRead:
    profile = await DriverRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        raise NotFoundError("Driver profile not found")
    return DriverProfileRead.model_validate(profile)


@router.patch(
    "/me/availability",
    response_model=DriverProfileRead,
    summary="Go online / offline",
)
async def set_availability(
    body: AvailabilityUpdate,
    service: DriverServiceDep,
    driver: CurrentDriver,
) -> DriverProfileRead:
    updated = await service.set_availability(driver, body.status)
    return DriverProfileRead.model_validate(updated)


@router.patch(
    "/me/location",
    response_model=DriverProfileRead,
    summary="Update my current location",
)
async def update_location(
    body: LocationUpdate,
    service: DriverServiceDep,
    driver: CurrentDriver,
) -> DriverProfileRead:
    updated = await service.update_location(driver, body.lat, body.lng)
    return DriverProfileRead.model_validate(updated)


@router.get(
    "/me/offers",
    response_model=list[RideOfferRead],
    summary="List pending ride offers near me",
)
async def list_offers(
    service: RideServiceDep, driver: CurrentDriver
) -> list[RideOfferRead]:
    return await service.list_offers(driver)


@router.post(
    "/me/rides/{ride_id}/accept",
    response_model=RideRead,
    summary="Accept a ride offer (atomic claim)",
)
async def accept_ride(
    ride_id: uuid.UUID, service: RideServiceDep, driver: CurrentDriver
) -> RideRead:
    return await service.accept_offer(driver, ride_id)


@router.post(
    "/me/rides/{ride_id}/reject",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Reject a ride offer",
)
async def reject_ride(
    ride_id: uuid.UUID, service: RideServiceDep, driver: CurrentDriver
) -> Response:
    await service.reject_offer(driver, ride_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/me/rides/{ride_id}/arrive",
    response_model=RideRead,
    summary="Mark arrival at pickup",
)
async def arrive(
    ride_id: uuid.UUID, service: RideServiceDep, driver: CurrentDriver
) -> RideRead:
    return await service.driver_arrived(driver, ride_id)


@router.post(
    "/me/rides/{ride_id}/start",
    response_model=RideRead,
    summary="Start the trip",
)
async def start(
    ride_id: uuid.UUID, service: RideServiceDep, driver: CurrentDriver
) -> RideRead:
    return await service.start_ride(driver, ride_id)


@router.post(
    "/me/rides/{ride_id}/complete",
    response_model=RideRead,
    summary="Complete the trip",
)
async def complete(
    ride_id: uuid.UUID, service: RideServiceDep, driver: CurrentDriver
) -> RideRead:
    return await service.complete_ride(driver, ride_id)
