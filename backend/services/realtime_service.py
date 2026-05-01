from __future__ import annotations

import asyncio
from threading import Lock

from fastapi import WebSocket
from logging_config import get_logger

logger = get_logger(__name__)


class NotificationHub:
    def __init__(self) -> None:
        self._connections: dict[int, dict[int, WebSocket]] = {}
        self._lock = Lock()

    async def connect(self, user_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._connections.setdefault(user_id, {})[id(websocket)] = websocket

    def disconnect(self, user_id: int, websocket: WebSocket) -> None:
        with self._lock:
            sockets = self._connections.get(user_id)
            if sockets is None:
                return
            sockets.pop(id(websocket), None)
            if not sockets:
                self._connections.pop(user_id, None)

    async def broadcast(self, user_id: int, payload: dict) -> None:
        with self._lock:
            sockets = list(self._connections.get(user_id, {}).values())

        if not sockets:
            return

        stale_connections: list[WebSocket] = []
        for websocket in sockets:
            try:
                await websocket.send_json(payload)
            except Exception:
                logger.exception("WebSocket send failed, marking stale")
                stale_connections.append(websocket)

        if not stale_connections:
            return

        with self._lock:
            current = self._connections.get(user_id)
            if current is None:
                return
            for websocket in stale_connections:
                current.pop(id(websocket), None)
            if not current:
                self._connections.pop(user_id, None)


notification_hub = NotificationHub()


def publish_notification_event(user_id: int, payload: dict) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("No running event loop to publish notification event")
        return

    loop.create_task(notification_hub.broadcast(user_id, payload))