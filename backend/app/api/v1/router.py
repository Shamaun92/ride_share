"""Aggregate all v1 endpoint routers under a single APIRouter."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    auth,
    drivers,
    notifications,
    pricing,
    promos,
    rides,
    users,
    wallet,
    ws,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(drivers.router)
api_router.include_router(rides.router)
api_router.include_router(wallet.router)
api_router.include_router(promos.router)
api_router.include_router(pricing.router)
api_router.include_router(notifications.router)
api_router.include_router(admin.router)
api_router.include_router(ws.router)
