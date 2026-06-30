"""Ride, offer, and dispatch schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    CancelledBy,
    OfferStatus,
    PaymentMethod,
    RideStatus,
    VehicleType,
)

Lat = Field(..., ge=-90.0, le=90.0)
Lng = Field(..., ge=-180.0, le=180.0)


class RideRequestCreate(BaseModel):
    pickup_lat: float = Lat
    pickup_lng: float = Lng
    pickup_address: str = Field(..., max_length=255)
    dropoff_lat: float = Lat
    dropoff_lng: float = Lng
    dropoff_address: str = Field(..., max_length=255)
    vehicle_type: VehicleType = VehicleType.CAR
    payment_method: PaymentMethod = PaymentMethod.CASH
    scheduled_for: datetime | None = None
    promo_code: str | None = Field(None, max_length=32)
    shared: bool = False

    @model_validator(mode="after")
    def _pickup_differs_from_dropoff(self) -> "RideRequestCreate":
        if (self.pickup_lat, self.pickup_lng) == (self.dropoff_lat, self.dropoff_lng):
            raise ValueError("pickup and dropoff cannot be identical")
        return self


class CancelRideRequest(BaseModel):
    reason: str | None = Field(None, max_length=255)


# ----------------------------- nested summaries ----------------------------- #
class VehicleSummary(BaseModel):
    vehicle_type: VehicleType
    make: str
    model: str
    color: str
    license_plate: str


class DriverSummary(BaseModel):
    driver_id: uuid.UUID
    full_name: str
    rating_avg: float
    current_lat: float | None
    current_lng: float | None
    vehicle: VehicleSummary | None = None


class RiderSummary(BaseModel):
    rider_id: uuid.UUID
    full_name: str


# -------------------------------- responses --------------------------------- #
class RideRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    rider_id: uuid.UUID
    driver_id: uuid.UUID | None
    status: RideStatus
    vehicle_type: VehicleType
    payment_method: PaymentMethod

    pickup_lat: float
    pickup_lng: float
    pickup_address: str
    dropoff_lat: float
    dropoff_lng: float
    dropoff_address: str

    distance_km: float
    estimated_fare: float | None
    final_fare: float | None
    discount_poisha: int = 0
    surge_bps: int = 10000
    is_shared: bool = False
    scheduled_for: datetime | None = None

    cancelled_by: CancelledBy | None
    cancellation_reason: str | None

    accepted_at: datetime | None
    arrived_at: datetime | None
    started_at: datetime | None
    completed_at: datetime | None
    cancelled_at: datetime | None
    created_at: datetime

    # Set explicitly by the serializer; never auto-populated from the ORM
    # relationship (whose shape differs from DriverSummary).
    driver: DriverSummary | None = Field(
        default=None, validation_alias=AliasChoices("_driver_summary")
    )


class RideRequestResult(BaseModel):
    """Returned immediately after requesting a ride."""

    ride: RideRead
    drivers_notified: int


class RideOfferRead(BaseModel):
    """A pending dispatch offer as seen by a driver."""

    id: uuid.UUID
    ride_id: uuid.UUID
    status: OfferStatus
    distance_to_pickup_km: float
    expires_at: datetime
    rider: RiderSummary
    pickup_lat: float
    pickup_lng: float
    pickup_address: str
    dropoff_lat: float
    dropoff_lng: float
    dropoff_address: str
    trip_distance_km: float
    estimated_fare: float | None
    vehicle_type: VehicleType
