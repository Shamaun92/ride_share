"""Admin/operations endpoints (require ADMIN role, except secret-gated bootstrap)."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Body, Query

from app.api.deps import (
    CurrentAdmin,
    DBSession,
    SchedulerServiceDep,
)
from app.core.config import settings
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.models.enums import VerificationStatus
from app.repositories.user import UserRepository
from app.schemas.driver import DriverProfileRead
from app.schemas.payment import PaymentRead
from app.schemas.promo import PromoCreate, PromoRead
from app.schemas.ride import RideRead
from app.services.admin_service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/bootstrap", summary="Promote a user to admin (secret-gated)")
async def bootstrap_admin(
    session: DBSession,
    email: str = Body(..., embed=True),
    secret: str = Body(..., embed=True),
) -> dict:
    if not settings.ADMIN_BOOTSTRAP_SECRET or secret != settings.ADMIN_BOOTSTRAP_SECRET:
        raise PermissionDeniedError("Invalid bootstrap secret")
    user = await UserRepository(session).get_by_email(email)
    if user is None:
        raise NotFoundError("User not found")
    await AdminService(session).bootstrap_admin(user.id)
    return {"status": "ok", "user_id": str(user.id), "role": "admin"}


@router.get("/metrics", summary="Platform metrics")
async def metrics(session: DBSession, admin: CurrentAdmin) -> dict:
    return await AdminService(session).metrics()


@router.get("/rides", response_model=list[RideRead], summary="All rides")
async def list_rides(
    session: DBSession,
    admin: CurrentAdmin,
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
) -> list[RideRead]:
    rides = await AdminService(session).list_rides(limit=limit, offset=offset)
    return [RideRead.model_validate(r) for r in rides]


@router.get(
    "/drivers", response_model=list[DriverProfileRead], summary="All drivers"
)
async def list_drivers(
    session: DBSession, admin: CurrentAdmin, limit: int = Query(50, le=200)
) -> list[DriverProfileRead]:
    drivers = await AdminService(session).list_drivers(limit=limit)
    return [DriverProfileRead.model_validate(d) for d in drivers]


@router.patch(
    "/drivers/{driver_id}/verify",
    response_model=DriverProfileRead,
    summary="Set a driver's verification status",
)
async def verify_driver(
    driver_id: uuid.UUID,
    session: DBSession,
    admin: CurrentAdmin,
    status: VerificationStatus = Body(..., embed=True),
) -> DriverProfileRead:
    profile = await AdminService(session).verify_driver(driver_id, status)
    return DriverProfileRead.model_validate(profile)


@router.post(
    "/promos", response_model=PromoRead, summary="Create a promo code"
)
async def create_promo(
    body: PromoCreate, session: DBSession, admin: CurrentAdmin
) -> PromoRead:
    promo = await AdminService(session).create_promo(body)
    return PromoRead.model_validate(promo)


@router.post(
    "/payments/{payment_id}/refund",
    response_model=PaymentRead,
    summary="Refund a payment (reverses its ledger transaction)",
)
async def refund_payment(
    payment_id: uuid.UUID, session: DBSession, admin: CurrentAdmin
) -> PaymentRead:
    payment = await AdminService(session).refund_payment(payment_id)
    return PaymentRead.model_validate(payment)


@router.post("/scheduler/run", summary="Dispatch due scheduled rides now")
async def run_scheduler(service: SchedulerServiceDep, admin: CurrentAdmin) -> dict:
    dispatched = await service.dispatch_due()
    return {"dispatched": dispatched}
