"""Admin/operations service: platform metrics and management actions."""
from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.exceptions import NotFoundError
from app.models.driver import DriverProfile
from app.models.enums import (
    DriverStatus,
    LedgerAccount,
    PromoKind,
    UserRole,
    VerificationStatus,
)
from app.models.ledger import LedgerEntry
from app.models.promo import PromoCode
from app.models.ride import Ride
from app.models.user import User
from app.repositories.driver import DriverRepository
from app.repositories.payment import PaymentRepository
from app.services.payment_service import PaymentService


class AdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.drivers = DriverRepository(session)
        self.payments = PaymentRepository(session)

    async def metrics(self) -> dict:
        status_rows = (
            await self.session.execute(
                select(Ride.status, func.count()).group_by(Ride.status)
            )
        ).all()
        rides_by_status = {s.value: int(c) for s, c in status_rows}

        revenue = (
            await self.session.execute(
                select(func.coalesce(func.sum(LedgerEntry.amount_poisha), 0)).where(
                    LedgerEntry.account == LedgerAccount.PLATFORM_REVENUE
                )
            )
        ).scalar_one()

        promo_spend = (
            await self.session.execute(
                select(func.coalesce(func.sum(LedgerEntry.amount_poisha), 0)).where(
                    LedgerEntry.account == LedgerAccount.PROMO_EXPENSE
                )
            )
        ).scalar_one()

        active_drivers = (
            await self.session.execute(
                select(func.count())
                .select_from(DriverProfile)
                .where(
                    DriverProfile.status.in_(
                        [DriverStatus.ONLINE, DriverStatus.ON_TRIP]
                    )
                )
            )
        ).scalar_one()

        total_users = (
            await self.session.execute(select(func.count()).select_from(User))
        ).scalar_one()

        return {
            "rides_by_status": rides_by_status,
            "total_rides": sum(rides_by_status.values()),
            "platform_revenue_poisha": int(revenue),
            "promo_expense_poisha": int(promo_spend),
            "active_drivers": int(active_drivers),
            "total_users": int(total_users),
        }

    async def list_rides(self, *, limit: int = 50, offset: int = 0) -> list[Ride]:
        result = await self.session.execute(
            select(Ride).order_by(Ride.created_at.desc()).limit(limit).offset(offset)
        )
        return list(result.scalars().all())

    async def list_drivers(self, *, limit: int = 50) -> list[DriverProfile]:
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(DriverProfile)
            .options(selectinload(DriverProfile.vehicles))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def verify_driver(
        self, driver_id: uuid.UUID, status: VerificationStatus
    ) -> DriverProfile:
        profile = await self.drivers.get_with_vehicles(driver_id)
        if profile is None:
            raise NotFoundError("Driver not found")
        profile.verification_status = status
        await self.session.commit()
        await self.session.refresh(profile)
        audit("admin.driver_verified", driver_id=driver_id, status=status)
        return profile

    async def create_promo(self, data) -> PromoCode:
        promo = PromoCode(
            code=data.code.upper(),
            kind=PromoKind(data.kind),
            value=data.value,
            max_discount_poisha=data.max_discount_poisha,
            min_fare_poisha=data.min_fare_poisha,
            usage_limit=data.usage_limit,
            per_user_limit=data.per_user_limit,
            valid_from=data.valid_from,
            valid_until=data.valid_until,
            is_active=True,
        )
        self.session.add(promo)
        await self.session.commit()
        await self.session.refresh(promo)
        audit("admin.promo_created", code=promo.code, kind=promo.kind, value=promo.value)
        return promo

    async def refund_payment(self, payment_id: uuid.UUID):
        payment = await self.payments.get_with_transaction(payment_id)
        if payment is None:
            raise NotFoundError("Payment not found")
        return await PaymentService(self.session).refund_payment(payment)

    async def bootstrap_admin(self, user_id: uuid.UUID) -> User:
        user = await self.session.get(User, user_id)
        if user is None:
            raise NotFoundError("User not found")
        user.role = UserRole.ADMIN
        await self.session.commit()
        await self.session.refresh(user)
        audit("admin.bootstrapped", user_id=user.id)
        return user
