"""Auth endpoints: register (rider/driver), login, refresh, logout."""
from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import AuthServiceDep, get_refresh_payload
from app.schemas.auth import LoginRequest
from app.schemas.driver import DriverRegister
from app.schemas.token import RefreshRequest, TokenPair
from app.schemas.user import UserCreate, UserRead

from app.api.rate_limit import ip_rate_limit

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a rider account",
    dependencies=[ip_rate_limit()],
)
async def register_rider(data: UserCreate, service: AuthServiceDep) -> UserRead:
    user = await service.register_rider(data)
    return UserRead.model_validate(user)


@router.post(
    "/register/driver",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Register a driver account (account + license + vehicle)",
    dependencies=[ip_rate_limit()],
)
async def register_driver(data: DriverRegister, service: AuthServiceDep) -> UserRead:
    user = await service.register_driver(data)
    return UserRead.model_validate(user)


@router.post(
    "/login",
    response_model=TokenPair,
    summary="Login with email or phone",
    dependencies=[ip_rate_limit()],
)
async def login(data: LoginRequest, service: AuthServiceDep) -> TokenPair:
    return await service.login(data.identifier, data.password)


@router.post("/refresh", response_model=TokenPair, summary="Rotate tokens")
async def refresh(body: RefreshRequest, service: AuthServiceDep) -> TokenPair:
    payload = get_refresh_payload(body.refresh_token)
    return await service.refresh_tokens(payload.sub, payload.jti, payload.role.value)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Revoke a refresh token",
)
async def logout(body: RefreshRequest, service: AuthServiceDep) -> Response:
    payload = get_refresh_payload(body.refresh_token)
    await service.logout(payload.sub, payload.jti)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
