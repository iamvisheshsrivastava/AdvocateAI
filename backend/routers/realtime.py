from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services.realtime_service import notification_hub

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/notifications/{user_id}")
async def notifications_socket(websocket: WebSocket, user_id: int):
    await notification_hub.connect(user_id, websocket)
    try:
        await websocket.send_json({"event": "connected", "user_id": user_id})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_hub.disconnect(user_id, websocket)
    finally:
        notification_hub.disconnect(user_id, websocket)