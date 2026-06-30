"""Import all models so Alembic's autogenerate and SQLAlchemy's mapper
registry see them.
"""
from app.models.base import Base
from app.models.driver import DriverProfile
from app.models.ledger import LedgerEntry, LedgerTransaction
from app.models.notification import Notification
from app.models.payment import Payment
from app.models.pool import RidePool
from app.models.promo import PromoCode, PromoRedemption
from app.models.rating import Rating
from app.models.ride import Ride
from app.models.ride_offer import RideOffer
from app.models.user import User
from app.models.vehicle import Vehicle
from app.models.wallet import Wallet

__all__ = [
    "Base",
    "User",
    "DriverProfile",
    "Vehicle",
    "Ride",
    "RideOffer",
    "Wallet",
    "LedgerTransaction",
    "LedgerEntry",
    "Payment",
    "Rating",
    "PromoCode",
    "PromoRedemption",
    "Notification",
    "RidePool",
]
