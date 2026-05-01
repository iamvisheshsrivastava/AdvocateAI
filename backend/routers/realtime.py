from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from logging_config import get_logger
from services.realtime_service import notification_hub

router = APIRouter(tags=["realtime"])
logger = get_logger(__name__)


@router.websocket("/ws/notifications/{user_id}")
async def notifications_socket(websocket: WebSocket, user_id: int):
    try:
        await notification_hub.connect(user_id, websocket)
    except Exception:
        logger.exception("Failed to connect websocket for user_id=%s", user_id)
        return
    try:
        await websocket.send_json({"event": "connected", "user_id": user_id})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_hub.disconnect(user_id, websocket)
    except Exception:
        logger.exception("Unexpected websocket error for user_id=%s", user_id)
    finally:
        notification_hub.disconnect(user_id, websocket)