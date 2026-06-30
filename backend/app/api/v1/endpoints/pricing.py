"""Surge preview endpoint."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SurgeServiceDep

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/surge", summary="Current surge multiplier at a location")
async def surge_preview(
    service: SurgeServiceDep,
    current_user: CurrentUser,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
) -> dict:
    bps = await service.compute_bps(lat, lng)
    return {"surge_bps": bps, "surge_multiplier": round(bps / 10000, 2)}
