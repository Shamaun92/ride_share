"""Enumerations shared across models and schemas."""
from __future__ import annotations

import enum


class UserRole(str, enum.Enum):
    RIDER = "rider"
    DRIVER = "driver"
    ADMIN = "admin"


class DriverStatus(str, enum.Enum):
    OFFLINE = "offline"
    ONLINE = "online"
    ON_TRIP = "on_trip"


class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class VehicleType(str, enum.Enum):
    CAR = "car"
    BIKE = "bike"
    CNG = "cng"


class RideStatus(str, enum.Enum):
    REQUESTED = "requested"      # rider created request, awaiting a driver
    ACCEPTED = "accepted"        # a driver claimed it, en route to pickup
    ARRIVED = "arrived"          # driver at pickup point
    IN_PROGRESS = "in_progress"  # rider on board, trip running
    SCHEDULED = "scheduled"      # booked for a future time, not yet dispatched
    COMPLETED = "completed"      # terminal: trip finished
    CANCELLED = "cancelled"      # terminal: cancelled by rider/driver/system
    EXPIRED = "expired"          # terminal: no driver accepted in time


class CancelledBy(str, enum.Enum):
    RIDER = "rider"
    DRIVER = "driver"
    SYSTEM = "system"


class OfferStatus(str, enum.Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class PaymentMethod(str, enum.Enum):
    WALLET = "wallet"
    CASH = "cash"


class PaymentStatus(str, enum.Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


class LedgerTxnKind(str, enum.Enum):
    RIDE_FARE = "ride_fare"
    TOP_UP = "top_up"
    CANCELLATION_FEE = "cancellation_fee"
    REFUND = "refund"
    PAYOUT = "payout"


class LedgerAccount(str, enum.Enum):
    """Logical accounts in the double-entry ledger. User-owned accounts carry a
    wallet_id on the posting; system accounts do not.
    """
    RIDER_WALLET = "rider_wallet"
    DRIVER_WALLET = "driver_wallet"
    PLATFORM_REVENUE = "platform_revenue"
    CASH_CLEARING = "cash_clearing"
    PROMO_EXPENSE = "promo_expense"


class RaterRole(str, enum.Enum):
    RIDER = "rider"
    DRIVER = "driver"


class PromoKind(str, enum.Enum):
    PERCENT = "percent"   # value is basis points off the fare
    FLAT = "flat"         # value is a flat poisha discount


class NotificationKind(str, enum.Enum):
    RIDE_SCHEDULED = "ride_scheduled"
    RIDE_DISPATCHED = "ride_dispatched"
    RIDE_ACCEPTED = "ride_accepted"
    DRIVER_ARRIVED = "driver_arrived"
    RIDE_STARTED = "ride_started"
    RIDE_COMPLETED = "ride_completed"
    RIDE_CANCELLED = "ride_cancelled"
    PROMO = "promo"
    GENERIC = "generic"


class RidePoolStatus(str, enum.Enum):
    OPEN = "open"        # accepting more co-riders
    MATCHED = "matched"  # at capacity or closed to new joins
    CLOSED = "closed"
