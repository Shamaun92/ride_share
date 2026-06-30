"""Ratings: riders rate drivers and vice versa, once per ride.

Rating a driver updates DriverProfile's running average in O(1).
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.models.enums import RaterRole, RideStatus
from app.models.rating import Rating
from app.models.user import User
from app.repositories.driver import DriverRepository
from app.repositories.rating import RatingRepository
from app.repositories.ride import RideRepository


class RatingService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ratings = RatingRepository(session)
        self.drivers = DriverRepository(session)
        self.rides = RideRepository(session)

    async def submit(
        self, ride_id, rater: User, score: int, comment: str | None
    ) -> Rating:
        ride = await self.rides.get_detail(ride_id)
        if ride is None:
            raise NotFoundError("Ride not found")
        if ride.status != RideStatus.COMPLETED:
            raise ConflictError("Only completed rides can be rated")

        if rater.id == ride.rider_id:
            role = RaterRole.RIDER
            if ride.driver is None:
                raise ConflictError("Ride has no driver to rate")
            ratee_user_id = ride.driver.user_id
        elif ride.driver is not None and ride.driver.user_id == rater.id:
            role = RaterRole.DRIVER
            ratee_user_id = ride.rider_id
        else:
            raise PermissionDeniedError("You did not take part in this ride")

        if await self.ratings.get_for_ride_and_rater(ride.id, rater.id):
            raise ConflictError("You already rated this ride")

        rating = Rating(
            ride_id=ride.id,
            rater_user_id=rater.id,
            ratee_user_id=ratee_user_id,
            rater_role=role,
            score=score,
            comment=comment,
        )
        self.session.add(rating)

        # Maintain the driver's running average when the rider rates them.
        if role == RaterRole.RIDER and ride.driver is not None:
            profile = ride.driver
            total = profile.rating_avg * profile.rating_count + score
            profile.rating_count += 1
            profile.rating_avg = round(total / profile.rating_count, 3)

        await self.session.commit()
        await self.session.refresh(rating)
        return rating
