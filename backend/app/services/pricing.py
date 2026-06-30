"""Fare engine.

All money is integer **poisha** (1 BDT = 100 poisha) to keep arithmetic exact.
A fare is: booking fee + base + distance + time, scaled by a vehicle multiplier
and a surge multiplier, floored at a configured minimum. `estimate` runs at
request time (duration inferred from distance and an assumed city speed);
`finalize` runs at completion using the real elapsed trip time.

Surge defaults to 1.0 — the multiplier is the seam Phase 6 plugs into.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings
from app.models.enums import VehicleType

# Vehicle multipliers in basis points (10000 = 1.0x).
_VEHICLE_BPS: dict[VehicleType, int] = {
    VehicleType.BIKE: 6000,
    VehicleType.CNG: 8000,
    VehicleType.CAR: 10000,
}


@dataclass(frozen=True)
class FareBreakdown:
    booking_fee: int
    base: int
    distance: int
    time: int
    vehicle_bps: int
    surge_bps: int
    subtotal: int          # before multipliers
    total: int             # final, after multipliers + minimum
    distance_km: float
    duration_min: float

    @property
    def total_bdt(self) -> float:
        return round(self.total / 100, 2)

    def as_dict(self) -> dict:
        d = {
            "booking_fee": self.booking_fee,
            "base": self.base,
            "distance": self.distance,
            "time": self.time,
            "vehicle_bps": self.vehicle_bps,
            "surge_bps": self.surge_bps,
            "subtotal": self.subtotal,
            "total": self.total,
            "distance_km": self.distance_km,
            "duration_min": self.duration_min,
            "currency": "BDT",
        }
        return d


def _compute(
    distance_km: float, duration_min: float, vehicle_type: VehicleType, surge_bps: int
) -> FareBreakdown:
    booking = settings.FARE_BOOKING_FEE_POISHA
    base = settings.FARE_BASE_POISHA
    distance = round(settings.FARE_PER_KM_POISHA * distance_km)
    time = round(settings.FARE_PER_MIN_POISHA * duration_min)
    subtotal = booking + base + distance + time

    vehicle_bps = _VEHICLE_BPS.get(vehicle_type, 10000)
    # Apply vehicle then surge (both in basis points).
    scaled = subtotal * vehicle_bps // 10000
    scaled = scaled * surge_bps // 10000
    total = max(scaled, settings.FARE_MIN_POISHA)

    return FareBreakdown(
        booking_fee=booking,
        base=base,
        distance=distance,
        time=time,
        vehicle_bps=vehicle_bps,
        surge_bps=surge_bps,
        subtotal=subtotal,
        total=total,
        distance_km=round(distance_km, 3),
        duration_min=round(duration_min, 2),
    )


def estimate(
    distance_km: float, vehicle_type: VehicleType, surge_bps: int = 10000
) -> FareBreakdown:
    """Quote at request time; duration inferred from an assumed city speed."""
    duration_min = (distance_km / max(settings.FARE_AVG_SPEED_KMH, 1e-6)) * 60.0
    return _compute(distance_km, duration_min, vehicle_type, surge_bps)


def finalize(
    distance_km: float,
    duration_min: float,
    vehicle_type: VehicleType,
    surge_bps: int = 10000,
) -> FareBreakdown:
    """Final fare at completion using the real elapsed trip duration."""
    return _compute(distance_km, duration_min, vehicle_type, surge_bps)


def commission_poisha(total_poisha: int) -> int:
    return total_poisha * settings.PLATFORM_COMMISSION_BPS // 10000
