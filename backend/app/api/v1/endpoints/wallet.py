"""Wallet endpoints: balance, statement, and top-up."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import CurrentUser, WalletServiceDep
from app.api.rate_limit import user_rate_limit
from app.schemas.payment import (
    LedgerEntryRead,
    TopUpRequest,
    WalletRead,
    WalletStatement,
)

router = APIRouter(prefix="/wallet", tags=["wallet"])


@router.get("", response_model=WalletStatement, summary="My wallet + recent activity")
async def get_wallet(service: WalletServiceDep, current_user: CurrentUser) -> WalletStatement:
    wallet, entries = await service.history(current_user.id)
    return WalletStatement(
        wallet=WalletRead.from_wallet(wallet),
        entries=[LedgerEntryRead.from_entry(e) for e in entries],
    )


@router.post(
    "/topup",
    response_model=WalletRead,
    summary="Add funds to my wallet",
    dependencies=[user_rate_limit()],
)
async def top_up(
    body: TopUpRequest, service: WalletServiceDep, current_user: CurrentUser
) -> WalletRead:
    wallet = await service.top_up(current_user.id, round(body.amount_bdt * 100))
    return WalletRead.from_wallet(wallet)
