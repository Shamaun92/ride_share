"""Payment settlement.

`settle_ride` runs inside the ride-completion transaction (flush-only; the
caller commits) so money movement and ride state change atomically. The
commission split sends the platform's cut to PLATFORM_REVENUE and the remainder
to the driver. For CASH the fare is exchanged off-ledger, so only the commission
the driver owes the platform is posted.
"""
from __future__ import annotations

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.audit import audit
from app.core.exceptions import NotFoundError
from app.models.enums import (
    LedgerAccount,
    LedgerTxnKind,
    PaymentMethod,
    PaymentStatus,
)
from app.models.payment import Payment
from app.repositories.payment import PaymentRepository
from app.services import pricing
from app.services.ledger_service import LedgerService, Posting
from app.services.pricing import FareBreakdown
from app.services.wallet_service import WalletService


class PaymentService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.ledger = LedgerService(session)
        self.wallets = WalletService(session)
        self.payments = PaymentRepository(session)

    async def settle_ride(
        self,
        *,
        ride_id: uuid.UUID,
        rider_user_id: uuid.UUID,
        driver_user_id: uuid.UUID,
        breakdown: FareBreakdown,
        method: PaymentMethod,
        gross_fare_poisha: int | None = None,
        promo_discount_poisha: int = 0,
    ) -> Payment:
        # gross_fare = fare actually owed for the trip (after any pool discount).
        # The promo discount is funded by the platform (PROMO_EXPENSE), so the
        # driver is paid on the gross fare while the rider is charged less.
        gross = gross_fare_poisha if gross_fare_poisha is not None else breakdown.total
        discount = max(0, min(promo_discount_poisha, gross))
        commission = pricing.commission_poisha(gross)
        driver_earnings = gross - commission
        rider_charge = gross - discount

        rider_wallet = await self.wallets.get_or_create(rider_user_id)
        driver_wallet = await self.wallets.get_or_create(driver_user_id)

        if method == PaymentMethod.WALLET:
            postings = [
                Posting(LedgerAccount.RIDER_WALLET, -rider_charge, wallet_id=rider_wallet.id),
                Posting(
                    LedgerAccount.DRIVER_WALLET, driver_earnings, wallet_id=driver_wallet.id
                ),
                Posting(LedgerAccount.PLATFORM_REVENUE, commission),
            ]
            if discount:
                postings.append(Posting(LedgerAccount.PROMO_EXPENSE, -discount))
        else:  # CASH: fare paid in cash; driver owes commission, platform funds promo
            postings = [
                Posting(
                    LedgerAccount.DRIVER_WALLET,
                    discount - commission,
                    wallet_id=driver_wallet.id,
                ),
                Posting(LedgerAccount.PLATFORM_REVENUE, commission),
            ]
            if discount:
                postings.append(Posting(LedgerAccount.PROMO_EXPENSE, -discount))

        txn = await self.ledger.post(
            LedgerTxnKind.RIDE_FARE,
            postings,
            ride_id=ride_id,
            memo=f"Ride fare ({method.value})",
        )

        detail = breakdown.as_dict()
        detail.update(
            {
                "gross_fare": gross,
                "promo_discount": discount,
                "rider_charge": rider_charge,
            }
        )
        payment = Payment(
            ride_id=ride_id,
            payer_user_id=rider_user_id,
            method=method,
            status=PaymentStatus.COMPLETED,
            amount_poisha=rider_charge,
            commission_poisha=commission,
            driver_earnings_poisha=driver_earnings,
            breakdown=detail,
            transaction_id=txn.id,
        )
        self.session.add(payment)
        await self.session.flush()
        audit(
            "payment.settled",
            ride_id=ride_id,
            rider_id=rider_user_id,
            driver_id=driver_user_id,
            method=method,
            gross_poisha=gross,
            rider_charge_poisha=rider_charge,
            commission_poisha=commission,
            promo_discount_poisha=discount,
        )
        return payment

    async def charge_cancellation_fee(
        self,
        *,
        ride_id: uuid.UUID,
        rider_user_id: uuid.UUID,
        driver_user_id: uuid.UUID,
        fee_poisha: int,
    ) -> Payment:
        rider_wallet = await self.wallets.get_or_create(rider_user_id)
        driver_wallet = await self.wallets.get_or_create(driver_user_id)
        txn = await self.ledger.post(
            LedgerTxnKind.CANCELLATION_FEE,
            [
                Posting(LedgerAccount.RIDER_WALLET, -fee_poisha, wallet_id=rider_wallet.id),
                Posting(LedgerAccount.DRIVER_WALLET, fee_poisha, wallet_id=driver_wallet.id),
            ],
            ride_id=ride_id,
            memo="Late cancellation fee",
        )
        payment = Payment(
            ride_id=ride_id,
            payer_user_id=rider_user_id,
            method=PaymentMethod.WALLET,
            status=PaymentStatus.COMPLETED,
            amount_poisha=fee_poisha,
            commission_poisha=0,
            driver_earnings_poisha=fee_poisha,
            breakdown={"cancellation_fee": fee_poisha, "currency": "BDT"},
            transaction_id=txn.id,
        )
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def refund_payment(self, payment: Payment) -> Payment:
        """Reverse a payment's ledger transaction and mark it refunded."""
        if payment.transaction is None:
            raise NotFoundError("Payment has no ledger transaction to reverse")
        await self.ledger.reverse(payment.transaction, memo="Payment refund")
        payment.status = PaymentStatus.REFUNDED
        await self.session.commit()
        await self.session.refresh(payment)
        audit("payment.refunded", payment_id=payment.id, ride_id=payment.ride_id, amount_poisha=payment.amount_poisha)
        return payment
