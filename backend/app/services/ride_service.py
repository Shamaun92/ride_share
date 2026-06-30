"""Ride lifecycle orchestration: request, dispatch, accept/reject, and the
driver progression (arrive -> start -> complete), plus cancellation.

Owns the transaction boundary and enforces the state machine. HTTP-agnostic:
raises domain exceptions. Serialization to API schemas lives here so endpoints
stay thin.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.geo import haversine_km
from app.models.driver import DriverProfile
from app.models.enums import (
    CancelledBy,
    DriverStatus,
    NotificationKind,
    OfferStatus,
    PaymentMethod,
    RidePoolStatus,
    RideStatus,
    UserRole,
)
from app.models.ride import Ride
from app.models.ride_offer import RideOffer
from app.models.user import User
from app.repositories.driver import DriverRepository
from app.repositories.payment import PaymentRepository
from app.repositories.rating import RatingRepository
from app.repositories.ride import RideOfferRepository, RideRepository
from app.schemas.payment import PaymentRead, RatingRead, RideReceipt
from app.schemas.ride import (
    DriverSummary,
    RideOfferRead,
    RideRead,
    RideRequestCreate,
    RideRequestResult,
    RiderSummary,
    VehicleSummary,
)
from app.services import pricing
from app.services.payment_service import PaymentService
from app.services.promo_service import PromoService
from app.services.surge_service import SurgeService
from app.services.pool_service import PoolService
from app.services.notification_service import NotificationService
from app.services.location_service import LocationService
from app.services.ride_state import assert_transition
from app.ws import events

logger = logging.getLogger("app.ws")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware(dt: datetime) -> datetime:
    """Normalise to aware UTC. Postgres returns aware datetimes; SQLite (used
    in tests) drops tzinfo, so we re-attach UTC before comparing.
    """
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


class RideService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.rides = RideRepository(session)
        self.offers = RideOfferRepository(session)
        self.drivers = DriverRepository(session)
        self.locations = LocationService(redis)
        self.payments = PaymentService(session)
        self.promos = PromoService(session)
        self.surge = SurgeService(session, redis)
        self.pools = PoolService(session)
        self.notifications = NotificationService(session, redis)

    # ------------------------------------------------------------------ #
    # Rider: request a ride
    # ------------------------------------------------------------------ #
    async def request_ride(
        self, rider: User, data: RideRequestCreate
    ) -> RideRequestResult:
        if await self.rides.get_active_for_rider(rider.id):
            raise ConflictError("You already have an active ride")

        scheduled_for = data.scheduled_for
        is_future = scheduled_for is not None and _ensure_aware(scheduled_for) > _now()

        distance = haversine_km(
            data.pickup_lat, data.pickup_lng, data.dropoff_lat, data.dropoff_lng
        )
        # Surge from live supply/demand (skipped for scheduled rides — priced at
        # dispatch time instead).
        surge_bps = (
            10000
            if is_future
            else await self.surge.compute_bps(data.pickup_lat, data.pickup_lng)
        )
        estimated = pricing.estimate(distance, data.vehicle_type, surge_bps)

        gross = estimated.total
        if data.shared:
            gross = gross * (10000 - settings.POOL_DISCOUNT_BPS) // 10000

        # Validate promo against the (pool-adjusted) estimate, but redeem later.
        promo = None
        discount = 0
        if data.promo_code:
            promo, discount = await self.promos.quote(
                data.promo_code, rider.id, gross
            )

        ride = Ride(
            rider_id=rider.id,
            status=RideStatus.SCHEDULED if is_future else RideStatus.REQUESTED,
            vehicle_type=data.vehicle_type,
            payment_method=data.payment_method,
            pickup_lat=data.pickup_lat,
            pickup_lng=data.pickup_lng,
            pickup_address=data.pickup_address,
            dropoff_lat=data.dropoff_lat,
            dropoff_lng=data.dropoff_lng,
            dropoff_address=data.dropoff_address,
            distance_km=round(distance, 3),
            estimated_fare=round((gross - discount) / 100, 2),
            scheduled_for=scheduled_for,
            promo_code_id=promo.id if promo else None,
            discount_poisha=discount,
            surge_bps=surge_bps,
            is_shared=data.shared,
        )
        await self.rides.add(ride)

        if data.shared:
            await self.pools.match_or_create(ride)

        if is_future:
            await self.session.commit()
            await self.notifications.push(
                user_id=rider.id,
                kind=NotificationKind.RIDE_SCHEDULED,
                title="Ride scheduled",
                body="Your ride is booked and will be dispatched shortly before pickup.",
                ride_id=ride.id,
            )
            fresh = await self.rides.get_detail(ride.id)
            assert fresh is not None
            return RideRequestResult(
                ride=self._serialize_ride(fresh), drivers_notified=0
            )

        notified = await self._dispatch_offers(ride)
        await self.session.commit()
        fresh = await self.rides.get_detail(ride.id)
        assert fresh is not None
        return RideRequestResult(
            ride=self._serialize_ride(fresh), drivers_notified=notified
        )

    # ------------------------------------------------------------------ #
    # Shared: read
    # ------------------------------------------------------------------ #
    async def get_ride_for_user(
        self, ride_id: uuid.UUID, user: User
    ) -> RideRead:
        ride = await self.rides.get_detail(ride_id)
        if ride is None:
            raise NotFoundError("Ride not found")
        await self._authorize_view(ride, user)
        return self._serialize_ride(ride)

    async def list_rides_for_user(self, user: User) -> list[RideRead]:
        if user.role == UserRole.DRIVER:
            profile = await self.drivers.get_by_user_id(user.id)
            if profile is None:
                return []
            rides = await self.rides.list_for_driver(profile.id)
        else:
            rides = await self.rides.list_for_rider(user.id)
        return [self._serialize_ride(r, with_driver=False) for r in rides]

    async def get_receipt(self, ride_id: uuid.UUID, user: User) -> RideReceipt:
        ride = await self.rides.get_detail(ride_id)
        if ride is None:
            raise NotFoundError("Ride not found")
        await self._authorize_view(ride, user)
        payment = await PaymentRepository(self.session).get_for_ride(ride_id)
        my_rating = await RatingRepository(self.session).get_for_ride_and_rater(
            ride_id, user.id
        )
        return RideReceipt(
            ride_id=ride.id,
            distance_km=ride.distance_km,
            final_fare_bdt=ride.final_fare,
            payment=PaymentRead.model_validate(payment) if payment else None,
            my_rating=RatingRead.model_validate(my_rating) if my_rating else None,
        )

    # ------------------------------------------------------------------ #
    # Rider/Driver: cancel
    # ------------------------------------------------------------------ #
    async def cancel_ride(
        self, ride_id: uuid.UUID, user: User, reason: str | None
    ) -> RideRead:
        ride = await self.rides.get_for_update(ride_id)
        if ride is None:
            raise NotFoundError("Ride not found")

        cancelled_by = await self._resolve_canceller(ride, user)
        previous_status = ride.status
        assert_transition(ride.status, RideStatus.CANCELLED)

        ride.status = RideStatus.CANCELLED
        ride.cancelled_by = cancelled_by
        ride.cancellation_reason = reason
        ride.cancelled_at = _now()

        # A rider who cancels after a driver committed (ACCEPTED/ARRIVED) pays a
        # late-cancellation fee that compensates the driver.
        charge_fee = (
            cancelled_by == CancelledBy.RIDER
            and previous_status in (RideStatus.ACCEPTED, RideStatus.ARRIVED)
            and ride.driver_id is not None
        )

        driver_user_id: uuid.UUID | None = None
        if ride.driver_id is not None:
            driver = await self.drivers.get(ride.driver_id)
            if driver is not None:
                driver_user_id = driver.user_id
                if driver.status == DriverStatus.ON_TRIP:
                    driver.status = DriverStatus.ONLINE
        await self.offers.expire_pending_for_ride(ride.id)

        if charge_fee and driver_user_id is not None:
            await self.payments.charge_cancellation_fee(
                ride_id=ride.id,
                rider_user_id=ride.rider_id,
                driver_user_id=driver_user_id,
                fee_poisha=settings.CANCELLATION_FEE_POISHA,
            )

        await self.session.commit()
        read = await self._finalize(ride_id)
        if cancelled_by == CancelledBy.RIDER and driver_user_id is not None:
            await self._notify(
                driver_user_id,
                NotificationKind.RIDE_CANCELLED,
                "Ride cancelled",
                "The rider cancelled this trip.",
                ride_id,
            )
        elif cancelled_by == CancelledBy.DRIVER:
            await self._notify(
                read.rider_id,
                NotificationKind.RIDE_CANCELLED,
                "Ride cancelled",
                "Your driver cancelled. You can request a new ride.",
                ride_id,
            )
        return read

    # ------------------------------------------------------------------ #
    # Driver: dispatch + progression
    # ------------------------------------------------------------------ #
    async def list_offers(self, driver: DriverProfile) -> list[RideOfferRead]:
        offers = await self.offers.list_pending_for_driver(driver.id, _now())
        return [self._serialize_offer(o) for o in offers]

    async def accept_offer(
        self, driver: DriverProfile, ride_id: uuid.UUID
    ) -> RideRead:
        if await self.rides.get_active_for_driver(driver.id):
            raise ConflictError("Finish your current ride before accepting another")

        offer = await self.offers.get_for_ride_and_driver(ride_id, driver.id)
        if offer is None:
            raise NotFoundError("No offer for this ride")
        if offer.status != OfferStatus.PENDING or _ensure_aware(offer.expires_at) <= _now():
            raise ConflictError("This offer is no longer available")

        won = await self.rides.claim(ride_id, driver.id, _now())
        if not won:
            offer.status = OfferStatus.EXPIRED
            await self.session.commit()
            raise ConflictError("Ride was already taken by another driver")

        offer.status = OfferStatus.ACCEPTED
        offer.responded_at = _now()
        await self.offers.expire_other_pending(ride_id, offer.id)
        driver.status = DriverStatus.ON_TRIP

        await self.session.commit()
        read = await self._finalize(ride_id)
        await self._notify(
            read.rider_id,
            NotificationKind.RIDE_ACCEPTED,
            "Driver on the way",
            "A driver accepted your ride and is heading to your pickup.",
            ride_id,
        )
        return read

    async def reject_offer(
        self, driver: DriverProfile, ride_id: uuid.UUID
    ) -> None:
        offer = await self.offers.get_for_ride_and_driver(ride_id, driver.id)
        if offer is None:
            raise NotFoundError("No offer for this ride")
        if offer.status != OfferStatus.PENDING:
            raise ConflictError("Offer already resolved")
        offer.status = OfferStatus.REJECTED
        offer.responded_at = _now()
        await self.session.commit()

    async def driver_arrived(
        self, driver: DriverProfile, ride_id: uuid.UUID
    ) -> RideRead:
        read = await self._advance(driver, ride_id, RideStatus.ARRIVED, "arrived_at")
        await self._notify(
            read.rider_id,
            NotificationKind.DRIVER_ARRIVED,
            "Your driver has arrived",
            "Your driver is waiting at the pickup point.",
            ride_id,
        )
        return read

    async def start_ride(
        self, driver: DriverProfile, ride_id: uuid.UUID
    ) -> RideRead:
        read = await self._advance(
            driver, ride_id, RideStatus.IN_PROGRESS, "started_at"
        )
        await self._notify(
            read.rider_id,
            NotificationKind.RIDE_STARTED,
            "Trip started",
            "Enjoy your ride. You can follow the trip live.",
            ride_id,
        )
        return read

    async def complete_ride(
        self, driver: DriverProfile, ride_id: uuid.UUID
    ) -> RideRead:
        ride = await self._load_owned_for_update(driver, ride_id)
        assert_transition(ride.status, RideStatus.COMPLETED)
        completed_at = _now()
        ride.status = RideStatus.COMPLETED
        ride.completed_at = completed_at

        # Final fare from the real elapsed trip duration.
        duration_min = 0.0
        if ride.started_at is not None:
            duration_min = max(
                (completed_at - _ensure_aware(ride.started_at)).total_seconds() / 60.0,
                0.0,
            )
        breakdown = pricing.finalize(
            ride.distance_km, duration_min, ride.vehicle_type, ride.surge_bps
        )
        gross = breakdown.total
        if ride.is_shared:
            gross = gross * (10000 - settings.POOL_DISCOUNT_BPS) // 10000

        discount = 0
        if ride.promo_code_id is not None:
            promo = await self.promos.promos.get(ride.promo_code_id)
            if promo is not None:
                discount = min(self.promos.compute_discount(promo, gross), gross)
                await self.promos.redeem(promo, ride.rider_id, ride.id, discount)
        ride.discount_poisha = discount
        ride.final_fare = round((gross - discount) / 100, 2)

        await self.payments.settle_ride(
            ride_id=ride.id,
            rider_user_id=ride.rider_id,
            driver_user_id=driver.user_id,
            breakdown=breakdown,
            method=ride.payment_method,
            gross_fare_poisha=gross,
            promo_discount_poisha=discount,
        )

        driver.status = DriverStatus.ONLINE
        await self.session.commit()
        read = await self._finalize(ride_id)
        await self._notify(
            ride.rider_id,
            NotificationKind.RIDE_COMPLETED,
            "Trip complete",
            f"Your fare is BDT {read.final_fare:.2f}. Tap to view the receipt.",
            ride_id,
        )
        return read

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #
    async def _find_nearby_drivers(
        self, lat: float, lng: float, vehicle_type
    ) -> list[tuple[DriverProfile, float]]:
        """Live proximity via Redis GEO, refined against the DB for status and
        vehicle type. Falls back to the SQL bounding-box scan if GEO is empty
        (cold cache / Redis unavailable) so dispatch degrades gracefully.
        """
        radius = settings.RIDE_SEARCH_RADIUS_KM
        limit = settings.RIDE_MAX_OFFERS
        hits = await self.locations.search_nearby(lat, lng, radius, count=limit * 3)
        if hits:
            dist_by_id: dict[str, float] = {m: d for m, d in hits}
            ids = [uuid.UUID(m) for m in dist_by_id]
            drivers = await self.drivers.get_many_with_vehicles(ids)
            scored: list[tuple[DriverProfile, float]] = []
            for d in drivers:
                if d.status != DriverStatus.ONLINE:
                    continue
                if not any(
                    v.is_active and v.vehicle_type == vehicle_type for v in d.vehicles
                ):
                    continue
                scored.append((d, dist_by_id[str(d.id)]))
            scored.sort(key=lambda pair: pair[1])
            if scored:
                return scored[:limit]
        # Fallback: relational bounding-box scan.
        return await self.drivers.find_nearby_available(
            lat=lat,
            lng=lng,
            radius_km=radius,
            vehicle_type=vehicle_type,
            limit=limit,
        )

    async def _dispatch_offers(self, ride: Ride) -> int:
        nearby = await self._find_nearby_drivers(
            ride.pickup_lat, ride.pickup_lng, ride.vehicle_type
        )
        expires_at = _now() + timedelta(seconds=settings.RIDE_OFFER_TTL_SECONDS)
        for driver, dist in nearby:
            self.session.add(
                RideOffer(
                    ride_id=ride.id,
                    driver_id=driver.id,
                    status=OfferStatus.PENDING,
                    distance_km=round(dist, 3),
                    expires_at=expires_at,
                )
            )
        return len(nearby)

    async def dispatch_scheduled_ride(self, ride: Ride) -> int:
        """Transition a due SCHEDULED ride to REQUESTED and offer it out."""
        assert_transition(ride.status, RideStatus.REQUESTED)
        ride.status = RideStatus.REQUESTED
        ride.surge_bps = await self.surge.compute_bps(
            ride.pickup_lat, ride.pickup_lng
        )
        est = pricing.estimate(ride.distance_km, ride.vehicle_type, ride.surge_bps)
        gross = est.total
        if ride.is_shared:
            gross = gross * (10000 - settings.POOL_DISCOUNT_BPS) // 10000
        ride.estimated_fare = round((gross - ride.discount_poisha) / 100, 2)
        notified = await self._dispatch_offers(ride)
        await self.session.commit()
        await self.notifications.push(
            user_id=ride.rider_id,
            kind=NotificationKind.RIDE_DISPATCHED,
            title="Finding your driver",
            body="Your scheduled ride is now searching for nearby drivers.",
            ride_id=ride.id,
        )
        return notified

    async def _finalize(self, ride_id: uuid.UUID) -> RideRead:
        """Reload the ride and broadcast its new status to both participants."""
        read = await self._reload(ride_id)
        await self._publish_status(read)
        return read

    async def _notify(
        self, user_id, kind: NotificationKind, title: str, body: str, ride_id=None
    ) -> None:
        try:
            await self.notifications.push(
                user_id=user_id, kind=kind, title=title, body=body, ride_id=ride_id
            )
        except Exception:  # pragma: no cover
            logger.exception("notification failed")

    async def _publish_status(self, read: RideRead) -> None:
        try:
            data: dict = {
                "ride_id": str(read.id),
                "status": read.status.value,
                "driver_id": str(read.driver_id) if read.driver_id else None,
                "final_fare": read.final_fare,
                "cancelled_by": read.cancelled_by.value if read.cancelled_by else None,
            }
            if read.driver is not None:
                data["driver"] = {
                    "driver_id": str(read.driver.driver_id),
                    "full_name": read.driver.full_name,
                    "rating_avg": read.driver.rating_avg,
                    "current_lat": read.driver.current_lat,
                    "current_lng": read.driver.current_lng,
                    "vehicle": (
                        read.driver.vehicle.model_dump(mode="json")
                        if read.driver.vehicle
                        else None
                    ),
                }
            await events.publish_event(
                self.redis, read.id, events.EventType.RIDE_STATUS, data
            )
        except Exception:  # pragma: no cover - never fail a transaction on RT
            logger.exception("Failed to publish ride status")

    async def _advance(
        self,
        driver: DriverProfile,
        ride_id: uuid.UUID,
        target: RideStatus,
        ts_field: str,
    ) -> RideRead:
        ride = await self._load_owned_for_update(driver, ride_id)
        assert_transition(ride.status, target)
        ride.status = target
        setattr(ride, ts_field, _now())
        await self.session.commit()
        return await self._finalize(ride_id)

    async def _load_owned_for_update(
        self, driver: DriverProfile, ride_id: uuid.UUID
    ) -> Ride:
        ride = await self.rides.get_for_update(ride_id)
        if ride is None:
            raise NotFoundError("Ride not found")
        if ride.driver_id != driver.id:
            raise PermissionDeniedError("You are not assigned to this ride")
        return ride

    async def _reload(self, ride_id: uuid.UUID) -> RideRead:
        ride = await self.rides.get_detail(ride_id)
        assert ride is not None
        return self._serialize_ride(ride)

    async def _authorize_view(self, ride: Ride, user: User) -> None:
        if user.role == UserRole.ADMIN or ride.rider_id == user.id:
            return
        if user.role == UserRole.DRIVER and ride.driver_id is not None:
            profile = await self.drivers.get_by_user_id(user.id)
            if profile is not None and profile.id == ride.driver_id:
                return
        raise PermissionDeniedError("You cannot view this ride")

    async def _resolve_canceller(self, ride: Ride, user: User) -> CancelledBy:
        if ride.rider_id == user.id:
            return CancelledBy.RIDER
        if user.role == UserRole.DRIVER and ride.driver_id is not None:
            profile = await self.drivers.get_by_user_id(user.id)
            if profile is not None and profile.id == ride.driver_id:
                return CancelledBy.DRIVER
        raise PermissionDeniedError("You cannot cancel this ride")

    # ------------------------------- serializers ------------------------ #
    @staticmethod
    def _driver_summary(driver: DriverProfile) -> DriverSummary:
        vehicle = next(
            (v for v in driver.vehicles if v.is_active),
            driver.vehicles[0] if driver.vehicles else None,
        )
        return DriverSummary(
            driver_id=driver.id,
            full_name=driver.user.full_name,
            rating_avg=driver.rating_avg,
            current_lat=driver.current_lat,
            current_lng=driver.current_lng,
            vehicle=(
                VehicleSummary(
                    vehicle_type=vehicle.vehicle_type,
                    make=vehicle.make,
                    model=vehicle.model,
                    color=vehicle.color,
                    license_plate=vehicle.license_plate,
                )
                if vehicle is not None
                else None
            ),
        )

    def _serialize_ride(self, ride: Ride, *, with_driver: bool = True) -> RideRead:
        payload = RideRead.model_validate(ride)
        if with_driver and ride.driver is not None:
            payload.driver = self._driver_summary(ride.driver)
        return payload

    @staticmethod
    def _serialize_offer(offer: RideOffer) -> RideOfferRead:
        ride = offer.ride
        return RideOfferRead(
            id=offer.id,
            ride_id=ride.id,
            status=offer.status,
            distance_to_pickup_km=offer.distance_km,
            expires_at=offer.expires_at,
            rider=RiderSummary(
                rider_id=ride.rider_id, full_name=ride.rider.full_name
            ),
            pickup_lat=ride.pickup_lat,
            pickup_lng=ride.pickup_lng,
            pickup_address=ride.pickup_address,
            dropoff_lat=ride.dropoff_lat,
            dropoff_lng=ride.dropoff_lng,
            dropoff_address=ride.dropoff_address,
            trip_distance_km=ride.distance_km,
            estimated_fare=ride.estimated_fare,
            vehicle_type=ride.vehicle_type,
        )
