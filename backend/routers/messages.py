from typing import Annotated

from fastapi import APIRouter, Query

from db.database import get_db_connection
from models.message import MessageSendRequest
from services.matching_service import refresh_lawyer_responsiveness
from services.notification_service import create_notification
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["messages"])


@router.post("/messages/send")
async def send_message(data: MessageSendRequest):
    content = data.content.strip()
    if not content:
        return {"success": False, "message": "Message content is required."}

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT c.client_id,
               EXISTS(SELECT 1 FROM lawyer_profiles WHERE lawyer_id = %s) AS sender_is_lawyer,
               EXISTS(SELECT 1 FROM lawyer_profiles WHERE lawyer_id = %s) AS receiver_is_lawyer
        FROM cases c
        WHERE c.case_id = %s
        """,
        (data.sender_id, data.receiver_id, data.case_id),
    )
    case_row = cur.fetchone()
    if not case_row:
        cur.close()
        conn.close()
        return {"success": False, "message": "Case not found."}

    cur.execute(
        """
        INSERT INTO messages (sender_id, receiver_id, case_id, content)
        VALUES (%s, %s, %s, %s)
        RETURNING message_id, created_at
        """,
        (data.sender_id, data.receiver_id, data.case_id, content),
    )
    inserted = cur.fetchone()

    cur.execute(
        """
        SELECT created_at
        FROM messages
        WHERE case_id = %s
          AND sender_id = %s
          AND receiver_id = %s
          AND message_id <> %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (data.case_id, data.receiver_id, data.sender_id, inserted[0]),
    )
    previous_message = cur.fetchone()

    conn.commit()
    cur.close()
    conn.close()

    create_notification(
        user_id=data.receiver_id,
        message=f"New message received on case #{data.case_id}.",
        notification_type="message",
    )

    sender_is_lawyer = bool(case_row[1])
    if sender_is_lawyer and previous_message:
        response_time = (inserted[1] - previous_message[0]).total_seconds() / 3600.0
        refresh_lawyer_responsiveness(data.sender_id, response_time_hours=max(response_time, 0.0))

    return {
        "success": True,
        "message_id": inserted[0],
        "created_at": str(inserted[1]),
    }


@router.get("/messages/{case_id}")
async def get_messages(case_id: int, user_id: Annotated[int | None, Query()] = None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT m.message_id, m.case_id, m.sender_id, sender.name, m.receiver_id, receiver.name,
               m.content, m.created_at
        FROM messages m
        JOIN users sender ON sender.id = m.sender_id
        JOIN users receiver ON receiver.id = m.receiver_id
        WHERE m.case_id = %s
        ORDER BY m.created_at ASC
        """,
        (case_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": row[0],
            "case_id": row[1],
            "sender_id": row[2],
            "sender_name": row[3],
            "receiver_id": row[4],
            "receiver_name": row[5],
            "content": row[6],
            "created_at": str(row[7]),
            "is_mine": user_id == row[2] if user_id is not None else False,
        }
        for row in rows
    ]