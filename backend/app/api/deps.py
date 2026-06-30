"""Reusable FastAPI dependencies: DB session, Redis, services, and the
authentication / authorization chain (current user + role guards).
"""
from __future__ import annotations

import uuid
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.redis import get_redis
from app.core.security import decode_token
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user import UserRepository
from app.schemas.token import TokenPayload
from app.services.auth_service import AuthService
from app.services.token_service import TokenService

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl=f"{settings.API_V1_PREFIX}/auth/login", auto_error=False
)

DBSession = Annotated[AsyncSession, Depends(get_db)]
RedisDep = Annotated[Redis, Depends(get_redis)]


def get_token_service(redis: RedisDep) -> TokenService:
    return TokenService(redis)


TokenServiceDep = Annotated[TokenService, Depends(get_token_service)]


def get_auth_service(session: DBSession, tokens: TokenServiceDep) -> AuthService:
    return AuthService(session, tokens)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


def _decode(token: str | None, expected_type: str) -> TokenPayload:
    if not token:
        raise AuthenticationError("Not authenticated")
    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise AuthenticationError("Token expired") from exc
    except jwt.PyJWTError as exc:
        raise AuthenticationError("Invalid token") from exc
    if payload.get("type") != expected_type:
        raise AuthenticationError("Wrong token type")
    return TokenPayload(**payload)


async def get_current_user(
    session: DBSession,
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> User:
    payload = _decode(token, "access")
    user = await UserRepository(session).get(payload.sub)
    if user is None or not user.is_active:
        raise AuthenticationError("User not found or inactive")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: UserRole):
    """Dependency factory enforcing role-based access control."""

    async def _guard(current_user: CurrentUser) -> User:
        if current_user.role not in roles:
            raise PermissionDeniedError(
                f"Requires one of roles: {[r.value for r in roles]}"
            )
        return current_user

    return _guard


def get_refresh_payload(token: str) -> TokenPayload:
    return _decode(token, "refresh")


# --------------------------------------------------------------------------- #
# Phase 2: ride + driver-operations dependencies
# --------------------------------------------------------------------------- #
from app.models.driver import DriverProfile  # noqa: E402
from app.repositories.driver import DriverRepository  # noqa: E402
from app.services.driver_service import DriverService  # noqa: E402
from app.services.ride_service import RideService  # noqa: E402


def get_ride_service(session: DBSession, redis: RedisDep) -> RideService:
    return RideService(session, redis)


RideServiceDep = Annotated[RideService, Depends(get_ride_service)]


def get_driver_service(session: DBSession, redis: RedisDep) -> DriverService:
    return DriverService(session, redis)


DriverServiceDep = Annotated[DriverService, Depends(get_driver_service)]


async def get_current_driver_profile(
    session: DBSession, current_user: CurrentUser
) -> DriverProfile:
    """Resolve the DriverProfile for the authenticated driver (RBAC + lookup)."""
    if current_user.role != UserRole.DRIVER:
        raise PermissionDeniedError("Driver role required")
    profile = await DriverRepository(session).get_by_user_id(current_user.id)
    if profile is None:
        raise AuthenticationError("Driver profile not found")
    return profile


CurrentDriver = Annotated[DriverProfile, Depends(get_current_driver_profile)]


# --------------------------------------------------------------------------- #
# Phase 4: wallet / payment / rating dependencies
# --------------------------------------------------------------------------- #
from app.services.payment_service import PaymentService  # noqa: E402
from app.services.rating_service import RatingService  # noqa: E402
from app.services.wallet_service import WalletService  # noqa: E402


def get_wallet_service(session: DBSession) -> WalletService:
    return WalletService(session)


WalletServiceDep = Annotated[WalletService, Depends(get_wallet_service)]


def get_payment_service(session: DBSession) -> PaymentService:
    return PaymentService(session)


PaymentServiceDep = Annotated[PaymentService, Depends(get_payment_service)]


def get_rating_service(session: DBSession) -> RatingService:
    return RatingService(session)


RatingServiceDep = Annotated[RatingService, Depends(get_rating_service)]


# --------------------------------------------------------------------------- #
# Phase 5/6: notifications, promos, surge, scheduler, admin
# --------------------------------------------------------------------------- #
from app.services.notification_service import NotificationService  # noqa: E402
from app.services.promo_service import PromoService  # noqa: E402
from app.services.scheduler_service import SchedulerService  # noqa: E402
from app.services.surge_service import SurgeService  # noqa: E402


def get_notification_service(session: DBSession, redis: RedisDep) -> NotificationService:
    return NotificationService(session, redis)


NotificationServiceDep = Annotated[NotificationService, Depends(get_notification_service)]


def get_promo_service(session: DBSession) -> PromoService:
    return PromoService(session)


PromoServiceDep = Annotated[PromoService, Depends(get_promo_service)]


def get_surge_service(session: DBSession, redis: RedisDep) -> SurgeService:
    return SurgeService(session, redis)


SurgeServiceDep = Annotated[SurgeService, Depends(get_surge_service)]


def get_scheduler_service(session: DBSession, redis: RedisDep) -> SchedulerService:
    return SchedulerService(session, redis)


SchedulerServiceDep = Annotated[SchedulerService, Depends(get_scheduler_service)]


async def get_current_admin(current_user: CurrentUser) -> User:
    if current_user.role != UserRole.ADMIN:
        raise PermissionDeniedError("Administrator access required")
    return current_user


CurrentAdmin = Annotated[User, Depends(get_current_admin)]
