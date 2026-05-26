from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from db.database import get_db_connection
from logging_config import get_logger
from services.notification_service import create_notification
from services.matching_service import refresh_lawyer_responsiveness
from services.realtime_service import case_hub, notification_hub, publish_case_message

router = APIRouter(tags=["realtime"])
logger = get_logger(__name__)


@router.websocket("/ws/notifications/{user_id}")
async def notifications_socket(websocket: WebSocket, user_id: int):
    try:
        await notification_hub.connect(user_id, websocket)
    except Exception:
        logger.exception("Failed to connect notification websocket for user_id=%s", user_id)
        return
    try:
        await websocket.send_json({"event": "connected", "user_id": user_id})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        notification_hub.disconnect(user_id, websocket)
    except Exception:
        logger.exception("Notification websocket error for user_id=%s", user_id)
    finally:
        notification_hub.disconnect(user_id, websocket)


@router.websocket("/ws/case/{case_id}/{user_id}")
async def case_socket(websocket: WebSocket, case_id: int, user_id: int):
    try:
        await case_hub.connect(case_id, websocket)
    except Exception:
        logger.exception("Failed to connect case websocket case_id=%s user_id=%s", case_id, user_id)
        return

    try:
        await websocket.send_json({"event": "connected", "case_id": case_id, "user_id": user_id})
        while True:
            data = await websocket.receive_json()
            event = data.get("event")

            if event == "send_message":
                content = str(data.get("content", "")).strip()
                receiver_id = data.get("receiver_id")
                if not content or not receiver_id:
                    continue

                conn = cur = None
                try:
                    conn = get_db_connection()
                    cur = conn.cursor()

                    cur.execute(
                        """
                        SELECT created_at FROM messages
                        WHERE case_id = %s AND sender_id = %s AND receiver_id = %s
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (case_id, receiver_id, user_id),
                    )
                    prev = cur.fetchone()

                    cur.execute(
                        """
                        INSERT INTO messages (sender_id, receiver_id, case_id, content)
                        VALUES (%s, %s, %s, %s)
                        RETURNING message_id, created_at
                        """,
                        (user_id, receiver_id, case_id, content),
                    )
                    msg_id, created_at = cur.fetchone()

                    cur.execute(
                        "SELECT EXISTS(SELECT 1 FROM lawyer_profiles WHERE lawyer_id = %s)",
                        (user_id,),
                    )
                    sender_is_lawyer = cur.fetchone()[0]

                    conn.commit()

                    if sender_is_lawyer and prev:
                        response_time = (created_at - prev[0]).total_seconds() / 3600.0
                        refresh_lawyer_responsiveness(user_id, response_time_hours=max(response_time, 0.0))

                    create_notification(
                        user_id=receiver_id,
                        message=f"New message on case #{case_id}.",
                        notification_type="message",
                    )

                    payload = {
                        "event": "new_message",
                        "message_id": msg_id,
                        "case_id": case_id,
                        "sender_id": user_id,
                        "receiver_id": receiver_id,
                        "content": content,
                        "created_at": str(created_at),
                    }
                    await case_hub.broadcast(case_id, payload)

                except Exception:
                    logger.exception("Error persisting websocket message case_id=%s", case_id)
                finally:
                    if cur:
                        cur.close()
                    if conn:
                        conn.close()

    except WebSocketDisconnect:
        case_hub.disconnect(case_id, websocket)
    except Exception:
        logger.exception("Case websocket error case_id=%s user_id=%s", case_id, user_id)
    finally:
        case_hub.disconnect(case_id, websocket)
