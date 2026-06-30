"""Notifications: persist a user-directed message and publish it live.

Persisted so they're queryable via REST; published to the user's real-time
channel (`rt:user:{id}`) for instant delivery (push/SMS-ready downstream).
"""
from __future__ import annotations

import logging
import uuid

from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import NotificationKind
from app.models.notification import Notification
from app.repositories.notification import NotificationRepository
from app.ws import events

logger = logging.getLogger("app.ws")


class NotificationService:
    def __init__(self, session: AsyncSession, redis: Redis) -> None:
        self.session = session
        self.redis = redis
        self.repo = NotificationRepository(session)

    async def push(
        self,
        *,
        user_id: uuid.UUID,
        kind: NotificationKind,
        title: str,
        body: str,
        data: dict | None = None,
        ride_id: uuid.UUID | None = None,
        commit: bool = True,
    ) -> Notification:
        notif = Notification(
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            data=data,
            ride_id=ride_id,
        )
        self.session.add(notif)
        if commit:
            await self.session.commit()
            await self.session.refresh(notif)
        else:
            await self.session.flush()

        try:
            await events.publish_user_event(
                self.redis,
                user_id,
                events.EventType.NOTIFICATION,
                {
                    "id": str(notif.id),
                    "kind": kind.value,
                    "title": title,
                    "body": body,
                    "ride_id": str(ride_id) if ride_id else None,
                },
            )
        except Exception:  # pragma: no cover - delivery is best-effort
            logger.exception("Failed to publish notification")
        return notif

    async def list(self, user_id: uuid.UUID, *, unread_only: bool = False):
        return await self.repo.list_for_user(user_id, unread_only=unread_only)

    async def unread_count(self, user_id: uuid.UUID) -> int:
        return await self.repo.unread_count(user_id)

    async def mark_read(self, notification_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        ok = await self.repo.mark_read(notification_id, user_id)
        await self.session.commit()
        return ok

    async def mark_all_read(self, user_id: uuid.UUID) -> int:
        n = await self.repo.mark_all_read(user_id)
        await self.session.commit()
        return n
