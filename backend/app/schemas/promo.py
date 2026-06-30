"""Promo, notification, and admin schemas."""
from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import NotificationKind, PromoKind


class PromoCreate(BaseModel):
    code: str = Field(..., max_length=32)
    kind: PromoKind
    value: int = Field(..., gt=0)
    max_discount_poisha: int | None = Field(None, ge=0)
    min_fare_poisha: int = Field(0, ge=0)
    usage_limit: int | None = Field(None, gt=0)
    per_user_limit: int = Field(1, gt=0)
    valid_from: datetime | None = None
    valid_until: datetime | None = None


class PromoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    kind: PromoKind
    value: int
    max_discount_poisha: int | None
    min_fare_poisha: int
    usage_limit: int | None
    per_user_limit: int
    used_count: int
    is_active: bool


class PromoQuoteRequest(BaseModel):
    code: str = Field(..., max_length=32)
    fare_poisha: int = Field(..., gt=0)


class PromoQuoteResult(BaseModel):
    code: str
    discount_poisha: int
    discount_bdt: float
    fare_after_poisha: int


class NotificationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: NotificationKind
    title: str
    body: str
    data: dict | None
    ride_id: uuid.UUID | None
    is_read: bool
    created_at: datetime


class NotificationList(BaseModel):
    unread: int
    items: list[NotificationRead]
