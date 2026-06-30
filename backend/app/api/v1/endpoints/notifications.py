"""Notification endpoints."""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Query, Response, status

from app.api.deps import CurrentUser, NotificationServiceDep
from app.core.exceptions import NotFoundError
from app.schemas.promo import NotificationList, NotificationRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationList, summary="My notifications")
async def list_notifications(
    service: NotificationServiceDep,
    current_user: CurrentUser,
    unread_only: bool = Query(False),
) -> NotificationList:
    items = await service.list(current_user.id, unread_only=unread_only)
    unread = await service.unread_count(current_user.id)
    return NotificationList(
        unread=unread, items=[NotificationRead.model_validate(i) for i in items]
    )


@router.post(
    "/{notification_id}/read",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Mark a notification read",
)
async def mark_read(
    notification_id: uuid.UUID,
    service: NotificationServiceDep,
    current_user: CurrentUser,
) -> Response:
    ok = await service.mark_read(notification_id, current_user.id)
    if not ok:
        raise NotFoundError("Notification not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/read-all", summary="Mark all my notifications read")
async def mark_all_read(
    service: NotificationServiceDep, current_user: CurrentUser
) -> dict:
    n = await service.mark_all_read(current_user.id)
    return {"marked_read": n}
