"""Authentication & registration business logic.

Owns the transaction boundary (commit/rollback) and orchestrates repositories,
password hashing, and token issuance. HTTP-agnostic: raises domain exceptions.
"""
from __future__ import annotations

from app.core.audit import audit

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationError, ConflictError, NotFoundError
from app.core.security import (
    create_access_token,
    create_refresh_token,
    hash_password,
    verify_password,
)
from app.models.driver import DriverProfile
from app.models.enums import UserRole
from app.models.user import User
from app.models.vehicle import Vehicle
from app.repositories.driver import DriverRepository
from app.repositories.user import UserRepository
from app.schemas.driver import DriverRegister
from app.schemas.token import TokenPair
from app.schemas.user import UserCreate
from app.services.token_service import TokenService


class AuthService:
    def __init__(self, session: AsyncSession, token_service: TokenService) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.drivers = DriverRepository(session)
        self.tokens = token_service

    # ----------------------------- registration ----------------------------- #
    async def register_rider(self, data: UserCreate) -> User:
        if await self.users.exists(data.email, data.phone):
            raise ConflictError("Email or phone already registered")
        user = User(
            email=data.email,
            phone=data.phone,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=UserRole.RIDER,
        )
        await self.users.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def register_driver(self, data: DriverRegister) -> User:
        if await self.users.exists(data.email, data.phone):
            raise ConflictError("Email or phone already registered")
        user = User(
            email=data.email,
            phone=data.phone,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
            role=UserRole.DRIVER,
        )
        await self.users.add(user)

        profile = DriverProfile(
            user_id=user.id,
            license_number=data.license_number,
        )
        await self.drivers.add(profile)

        vehicle = Vehicle(
            driver_id=profile.id,
            vehicle_type=data.vehicle.vehicle_type,
            make=data.vehicle.make,
            model=data.vehicle.model,
            color=data.vehicle.color,
            license_plate=data.vehicle.license_plate,
        )
        self.session.add(vehicle)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    # -------------------------------- login --------------------------------- #
    async def authenticate(self, identifier: str, password: str) -> User:
        user = await self.users.get_by_identifier(identifier)
        if user is None or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Invalid credentials")
        if not user.is_active:
            raise AuthenticationError("Account is disabled")
        return user

    async def issue_tokens(self, user: User) -> TokenPair:
        access = create_access_token(user.id, user.role.value)
        refresh, jti = create_refresh_token(user.id, user.role.value)
        await self.tokens.store_refresh(user.id, jti)
        return TokenPair(access_token=access, refresh_token=refresh)

    async def login(self, identifier: str, password: str) -> TokenPair:
        user = await self.authenticate(identifier, password)
        tokens = await self.issue_tokens(user)
        audit("auth.login", user_id=user.id, role=user.role, method="password")
        return tokens

    # ------------------------------- refresh -------------------------------- #
    async def refresh_tokens(
        self, user_id: uuid.UUID, jti: str, role: str
    ) -> TokenPair:
        if not await self.tokens.is_valid(user_id, jti):
            raise AuthenticationError("Refresh token revoked or expired")
        user = await self.users.get(user_id)
        if user is None or not user.is_active:
            raise NotFoundError("User not found")
        # Rotate: invalidate the used refresh token, issue a fresh pair.
        await self.tokens.revoke(user_id, jti)
        return await self.issue_tokens(user)

    async def logout(self, user_id: uuid.UUID, jti: str) -> None:
        await self.tokens.revoke(user_id, jti)
