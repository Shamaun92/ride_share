"""Driver registration and profile schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.enums import DriverStatus, VehicleType, VerificationStatus


class VehicleCreate(BaseModel):
    vehicle_type: VehicleType
    make: str = Field(..., max_length=64)
    model: str = Field(..., max_length=64)
    color: str = Field(..., max_length=32)
    license_plate: str = Field(..., max_length=32)


class VehicleRead(VehicleCreate):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_active: bool


class DriverRegister(BaseModel):
    """Single-call driver onboarding: account + license + first vehicle."""

    email: EmailStr
    phone: str = Field(..., min_length=6, max_length=20)
    full_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)
    license_number: str = Field(..., max_length=64)
    vehicle: VehicleCreate


class DriverProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    license_number: str
    verification_status: VerificationStatus
    status: DriverStatus
    rating_avg: float
    rating_count: int
    current_lat: float | None
    current_lng: float | None
    created_at: datetime
    vehicles: list[VehicleRead] = []


class AvailabilityUpdate(BaseModel):
    """Drivers toggle ONLINE/OFFLINE only; ON_TRIP is system-managed."""

    status: DriverStatus

    @field_validator("status")
    @classmethod
    def _only_online_offline(cls, v: DriverStatus) -> DriverStatus:
        if v not in (DriverStatus.ONLINE, DriverStatus.OFFLINE):
            raise ValueError("status must be 'online' or 'offline'")
        return v


class LocationUpdate(BaseModel):
    lat: float = Field(..., ge=-90.0, le=90.0)
    lng: float = Field(..., ge=-180.0, le=180.0)
