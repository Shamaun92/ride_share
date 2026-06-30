"""Rider-facing and shared ride endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status

from app.api.deps import (
    CurrentUser,
    RatingServiceDep,
    RideServiceDep,
    require_roles,
)
from app.api.rate_limit import user_rate_limit
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.payment import RatingCreate, RatingRead, RideReceipt
from app.schemas.ride import (
    CancelRideRequest,
    RideRead,
    RideRequestCreate,
    RideRequestResult,
)

router = APIRouter(prefix="/rides", tags=["rides"])


@router.post(
    "",
    response_model=RideRequestResult,
    status_code=status.HTTP_201_CREATED,
    summary="Request a ride (dispatches offers to nearby drivers)",
    dependencies=[user_rate_limit()],
)
async def request_ride(
    data: RideRequestCreate,
    service: RideServiceDep,
    rider: User = Depends(require_roles(UserRole.RIDER)),
) -> RideRequestResult:
    return await service.request_ride(rider, data)


@router.get("", response_model=list[RideRead], summary="List my rides")
async def list_my_rides(
    service: RideServiceDep, current_user: CurrentUser
) -> list[RideRead]:
    return await service.list_rides_for_user(current_user)


@router.get(
    "/{ride_id}",
    response_model=RideRead,
    summary="Get a ride (rider or assigned driver)",
)
async def get_ride(
    ride_id: uuid.UUID, service: RideServiceDep, current_user: CurrentUser
) -> RideRead:
    return await service.get_ride_for_user(ride_id, current_user)


@router.post(
    "/{ride_id}/cancel",
    response_model=RideRead,
    summary="Cancel a ride (rider or assigned driver)",
)
async def cancel_ride(
    ride_id: uuid.UUID,
    body: CancelRideRequest,
    service: RideServiceDep,
    current_user: CurrentUser,
) -> RideRead:
    return await service.cancel_ride(ride_id, current_user, body.reason)


@router.get(
    "/{ride_id}/receipt",
    response_model=RideReceipt,
    summary="Ride receipt: fare breakdown, payment, and my rating",
)
async def get_receipt(
    ride_id: uuid.UUID, service: RideServiceDep, current_user: CurrentUser
) -> RideReceipt:
    return await service.get_receipt(ride_id, current_user)


@router.post(
    "/{ride_id}/rate",
    response_model=RatingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Rate the other party (after completion)",
)
async def rate_ride(
    ride_id: uuid.UUID,
    body: RatingCreate,
    service: RatingServiceDep,
    current_user: CurrentUser,
) -> RatingRead:
    rating = await service.submit(ride_id, current_user, body.score, body.comment)
    return RatingRead.model_validate(rating)
