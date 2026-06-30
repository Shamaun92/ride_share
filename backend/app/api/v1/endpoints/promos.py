"""Promo preview endpoint (creation is admin-only)."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, PromoServiceDep
from app.schemas.promo import PromoQuoteRequest, PromoQuoteResult

router = APIRouter(prefix="/promos", tags=["promos"])


@router.post("/quote", response_model=PromoQuoteResult, summary="Preview a promo")
async def quote_promo(
    body: PromoQuoteRequest, service: PromoServiceDep, current_user: CurrentUser
) -> PromoQuoteResult:
    promo, discount = await service.quote(body.code, current_user.id, body.fare_poisha)
    return PromoQuoteResult(
        code=promo.code,
        discount_poisha=discount,
        discount_bdt=round(discount / 100, 2),
        fare_after_poisha=body.fare_poisha - discount,
    )
