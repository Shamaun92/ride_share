"""Phase 4 tests: fare engine, ledger, wallet, settlement, refunds, ratings."""
from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.models.enums import LedgerTxnKind, VehicleType
from app.services import pricing
from app.services.ledger_service import LedgerService, Posting
from app.models.enums import LedgerAccount
from tests.helpers import (
    ride_body,
    auth,
    go_online,
    login,
    me_id,
    register_driver,
    register_rider,
    run_ride_to_completion,
    topup,
)

pytestmark = pytest.mark.asyncio


# --------------------------------------------------------------------------- #
# Fare engine (pure)
# --------------------------------------------------------------------------- #
async def test_fare_engine_components_and_floor() -> None:
    car = pricing.estimate(10.0, VehicleType.CAR)
    # 1000 booking + 5000 base + 30000 distance + 6000 time (30 min @ 20km/h)
    assert car.subtotal == 42000
    assert car.total == 42000
    assert car.total_bdt == 420.0

    bike = pricing.estimate(10.0, VehicleType.BIKE)
    assert bike.total == 42000 * 6000 // 10000  # 0.6x

    # commission is 20%
    assert pricing.commission_poisha(42000) == 8400

    # minimum fare floor
    assert pricing.estimate(0.0, VehicleType.CAR).total == 6000


# --------------------------------------------------------------------------- #
# Ledger invariant
# --------------------------------------------------------------------------- #
async def test_ledger_rejects_unbalanced(db_session) -> None:
    from app.core.exceptions import ValidationError

    svc = LedgerService(db_session)
    with pytest.raises(ValidationError):
        await svc.post(
            LedgerTxnKind.TOP_UP,
            [Posting(LedgerAccount.PLATFORM_REVENUE, 100)],  # sums to 100, not 0
        )


# --------------------------------------------------------------------------- #
# Wallet top-up
# --------------------------------------------------------------------------- #
async def test_wallet_topup(client: AsyncClient) -> None:
    rider = await register_rider(client)
    token = await login(client, rider["email"])
    w = await topup(client, token, 500)
    assert w["balance_poisha"] == 50000
    assert w["balance_bdt"] == 500.0

    r = await client.get("/api/v1/wallet", headers=auth(token))
    assert r.status_code == 200
    body = r.json()
    assert body["wallet"]["balance_poisha"] == 50000
    assert len(body["entries"]) == 1


# --------------------------------------------------------------------------- #
# Wallet ride settlement + commission split
# --------------------------------------------------------------------------- #
async def test_wallet_ride_settlement_splits_commission(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)

    await topup(client, rtoken, 1000)  # 100000 poisha
    ride_id = await run_ride_to_completion(
        client, rtoken, dtoken, payment_method="wallet"
    )

    receipt = (await client.get(
        f"/api/v1/rides/{ride_id}/receipt", headers=auth(rtoken)
    )).json()
    pay = receipt["payment"]
    assert pay["method"] == "wallet"
    assert pay["status"] == "completed"
    fare = pay["amount_poisha"]
    commission = pay["commission_poisha"]
    earnings = pay["driver_earnings_poisha"]
    assert commission == fare * 2000 // 10000
    assert earnings == fare - commission

    rider_w = (await client.get("/api/v1/wallet", headers=auth(rtoken))).json()["wallet"]
    driver_w = (await client.get("/api/v1/wallet", headers=auth(dtoken))).json()["wallet"]
    assert rider_w["balance_poisha"] == 100000 - fare
    assert driver_w["balance_poisha"] == earnings


# --------------------------------------------------------------------------- #
# Cash settlement: only the commission moves (driver owes platform)
# --------------------------------------------------------------------------- #
async def test_cash_ride_settlement(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)

    ride_id = await run_ride_to_completion(
        client, rtoken, dtoken, payment_method="cash"
    )
    receipt = (await client.get(
        f"/api/v1/rides/{ride_id}/receipt", headers=auth(rtoken)
    )).json()
    commission = receipt["payment"]["commission_poisha"]

    # rider wallet untouched; driver owes the commission (negative balance)
    rider_w = (await client.get("/api/v1/wallet", headers=auth(rtoken))).json()["wallet"]
    driver_w = (await client.get("/api/v1/wallet", headers=auth(dtoken))).json()["wallet"]
    assert rider_w["balance_poisha"] == 0
    assert driver_w["balance_poisha"] == -commission


# --------------------------------------------------------------------------- #
# Cancellation fee + refund reversal
# --------------------------------------------------------------------------- #
async def test_cancellation_fee_then_refund(client: AsyncClient, db_session) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)

    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(rtoken))
    ride_id = r.json()["ride"]["id"]
    await client.post(f"/api/v1/drivers/me/rides/{ride_id}/accept", headers=auth(dtoken))
    # rider cancels AFTER acceptance -> late fee
    rc = await client.post(
        f"/api/v1/rides/{ride_id}/cancel", json={"reason": "late"}, headers=auth(rtoken)
    )
    assert rc.status_code == 200

    rider_w = (await client.get("/api/v1/wallet", headers=auth(rtoken))).json()["wallet"]
    driver_w = (await client.get("/api/v1/wallet", headers=auth(dtoken))).json()["wallet"]
    assert rider_w["balance_poisha"] == -3000
    assert driver_w["balance_poisha"] == 3000

    # Refund the cancellation fee via the service (admin/dispute path).
    from app.repositories.payment import PaymentRepository
    from app.services.payment_service import PaymentService
    import uuid

    payment = await PaymentRepository(db_session).get_for_ride(uuid.UUID(ride_id))
    assert payment is not None
    await PaymentService(db_session).refund_payment(payment)

    rider_w = (await client.get("/api/v1/wallet", headers=auth(rtoken))).json()["wallet"]
    driver_w = (await client.get("/api/v1/wallet", headers=auth(dtoken))).json()["wallet"]
    assert rider_w["balance_poisha"] == 0
    assert driver_w["balance_poisha"] == 0


# --------------------------------------------------------------------------- #
# Ratings
# --------------------------------------------------------------------------- #
async def test_rating_updates_driver_average(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    driver = await register_driver(client)
    dtoken = await login(client, driver["email"])
    await go_online(client, dtoken, 23.7809, 90.4078)

    ride_id = await run_ride_to_completion(client, rtoken, dtoken, payment_method="cash")

    r = await client.post(
        f"/api/v1/rides/{ride_id}/rate",
        json={"score": 4, "comment": "Smooth ride"},
        headers=auth(rtoken),
    )
    assert r.status_code == 201, r.text

    prof = (await client.get("/api/v1/drivers/me", headers=auth(dtoken))).json()
    assert prof["rating_count"] == 1
    assert prof["rating_avg"] == 4.0

    # double-rating the same ride is rejected
    r2 = await client.post(
        f"/api/v1/rides/{ride_id}/rate", json={"score": 5}, headers=auth(rtoken)
    )
    assert r2.status_code == 409


async def test_cannot_rate_incomplete_ride(client: AsyncClient) -> None:
    rider = await register_rider(client)
    rtoken = await login(client, rider["email"])
    r = await client.post("/api/v1/rides", json=ride_body(), headers=auth(rtoken))
    ride_id = r.json()["ride"]["id"]
    rr = await client.post(
        f"/api/v1/rides/{ride_id}/rate", json={"score": 5}, headers=auth(rtoken)
    )
    assert rr.status_code == 409
