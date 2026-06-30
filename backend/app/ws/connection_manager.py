"""WebSocketHub: per-instance socket registry + Redis Pub/Sub fan-out.

Sockets are registered under their full Redis channel (e.g. `rt:ride:{id}` or
`rt:user:{id}`). One reader task pattern-subscribes to every real-time pattern
and forwards each published envelope to the sockets this instance holds for the
originating channel. Publishers only `publish_event`/`publish_user_event` and
stay oblivious to where recipients are connected — correct under horizontal
scaling.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict

from fastapi import WebSocket
from redis.asyncio import Redis

from app.ws.events import ALL_PATTERNS

logger = logging.getLogger("app.ws")


class WebSocketHub:
    def __init__(self) -> None:
        self._local: dict[str, set[WebSocket]] = defaultdict(set)
        self._redis: Redis | None = None
        self._pubsub = None
        self._reader: asyncio.Task | None = None

    async def start(self, redis: Redis) -> None:
        self._redis = redis
        self._pubsub = redis.pubsub()
        await self._pubsub.psubscribe(*ALL_PATTERNS)
        self._reader = asyncio.create_task(self._reader_loop())
        logger.info("WebSocketHub started")

    async def stop(self) -> None:
        if self._reader is not None:
            self._reader.cancel()
            try:
                await self._reader
            except asyncio.CancelledError:
                pass
            self._reader = None
        if self._pubsub is not None:
            await self._pubsub.punsubscribe(*ALL_PATTERNS)
            await self._pubsub.aclose()
            self._pubsub = None

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._local[channel].add(websocket)

    def disconnect(self, channel: str, websocket: WebSocket) -> None:
        sockets = self._local.get(channel)
        if not sockets:
            return
        sockets.discard(websocket)
        if not sockets:
            self._local.pop(channel, None)

    async def send_personal(self, websocket: WebSocket, message: str) -> None:
        await websocket.send_text(message)

    async def _dispatch_local(self, channel: str, message: str) -> None:
        sockets = self._local.get(channel)
        if not sockets:
            return
        dead: list[WebSocket] = []
        for ws in list(sockets):
            try:
                await ws.send_text(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(channel, ws)

    async def _reader_loop(self) -> None:
        assert self._pubsub is not None
        try:
            async for raw in self._pubsub.listen():
                if raw is None or raw.get("type") != "pmessage":
                    continue
                channel = raw["channel"]
                if isinstance(channel, bytes):
                    channel = channel.decode()
                data = raw["data"]
                if isinstance(data, bytes):
                    data = data.decode()
                await self._dispatch_local(channel, data)
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover
            logger.exception("WebSocketHub reader loop crashed")


hub = WebSocketHub()
