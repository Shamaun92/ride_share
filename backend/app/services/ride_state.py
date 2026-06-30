"""Ride state machine: the single source of truth for legal transitions.

Centralising this keeps every entry point (rider cancel, driver accept/start/
complete, system expiry) consistent and makes illegal transitions a 409 rather
than silent data corruption.
"""
from __future__ import annotations

from app.core.exceptions import ConflictError
from app.models.enums import RideStatus

_ALLOWED: dict[RideStatus, set[RideStatus]] = {
    RideStatus.SCHEDULED: {
        RideStatus.REQUESTED,
        RideStatus.CANCELLED,
        RideStatus.EXPIRED,
    },
    RideStatus.REQUESTED: {
        RideStatus.ACCEPTED,
        RideStatus.CANCELLED,
        RideStatus.EXPIRED,
    },
    RideStatus.ACCEPTED: {RideStatus.ARRIVED, RideStatus.CANCELLED},
    RideStatus.ARRIVED: {RideStatus.IN_PROGRESS, RideStatus.CANCELLED},
    RideStatus.IN_PROGRESS: {RideStatus.COMPLETED},
    RideStatus.COMPLETED: set(),
    RideStatus.CANCELLED: set(),
    RideStatus.EXPIRED: set(),
}

ACTIVE_STATUSES: frozenset[RideStatus] = frozenset(
    {
        RideStatus.REQUESTED,
        RideStatus.ACCEPTED,
        RideStatus.ARRIVED,
        RideStatus.IN_PROGRESS,
    }
)


def assert_transition(current: RideStatus, target: RideStatus) -> None:
    if target not in _ALLOWED[current]:
        raise ConflictError(
            f"Illegal ride transition: {current.value} -> {target.value}"
        )
