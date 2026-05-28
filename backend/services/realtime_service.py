from __future__ import annotations

import asyncio
from threading import Lock

from fastapi import WebSocket
from logging_config import get_logger

logger = get_logger(__name__)


class _Hub:
    """Generic WebSocket hub keyed by an integer (user_id or case_id)."""

    def __init__(self) -> None:
        self._connections: dict[int, dict[int, WebSocket]] = {}
        self._lock = Lock()

    async def connect(self, key: int, websocket: WebSocket) -> None:
        await websocket.accept()
        with self._lock:
            self._connections.setdefault(key, {})[id(websocket)] = websocket

    def disconnect(self, key: int, websocket: WebSocket) -> None:
        with self._lock:
            sockets = self._connections.get(key)
            if sockets is None:
                return
            sockets.pop(id(websocket), None)
            if not sockets:
                self._connections.pop(key, None)

    async def broadcast(self, key: int, payload: dict) -> None:
        with self._lock:
            sockets = list(self._connections.get(key, {}).values())

        if not sockets:
            return

        stale: list[WebSocket] = []
        for ws in sockets:
            try:
                await ws.send_json(payload)
            except Exception:
                logger.exception("WebSocket send failed, marking stale")
                stale.append(ws)

        if stale:
            with self._lock:
                current = self._connections.get(key)
                if current:
                    for ws in stale:
                        current.pop(id(ws), None)
                    if not current:
                        self._connections.pop(key, None)


notification_hub = _Hub()
case_hub = _Hub()


def publish_notification_event(user_id: int, payload: dict) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("No running event loop to publish notification event")
        return
    loop.create_task(notification_hub.broadcast(user_id, payload))


def publish_case_message(case_id: int, payload: dict) -> None:
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        logger.debug("No running event loop to publish case message")
        return
    loop.create_task(case_hub.broadcast(case_id, payload))
