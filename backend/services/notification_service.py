from db.database import get_db_connection

from services.realtime_service import publish_notification_event


def create_notification(user_id: int, message: str, notification_type: str) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO notifications (user_id, message, type)
        VALUES (%s, %s, %s)
        RETURNING id, user_id, message, type, is_read, created_at
        """,
        (user_id, message.strip(), notification_type.strip()),
    )
    row = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()

    if row:
        payload = {
            "event": "notification.created",
            "notification": {
                "id": row[0],
                "user_id": row[1],
                "message": row[2],
                "type": row[3],
                "is_read": row[4],
                "created_at": str(row[5]),
            },
        }
        publish_notification_event(user_id, payload)


def get_notifications(user_id: int):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, message, type, is_read, created_at
        FROM notifications
        WHERE user_id = %s
        ORDER BY created_at DESC
        """,
        (user_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {
            "id": row[0],
            "message": row[1],
            "type": row[2],
            "is_read": row[3],
            "created_at": str(row[4]),
        }
        for row in rows
    ]


def mark_notifications_read(user_id: int, notification_ids: list[int] | None = None) -> None:
    conn = get_db_connection()
    cur = conn.cursor()
    if notification_ids:
        cur.execute(
            """
            UPDATE notifications
            SET is_read = TRUE
            WHERE user_id = %s AND id = ANY(%s)
            """,
            (user_id, notification_ids),
        )
    else:
        cur.execute(
            """
            UPDATE notifications
            SET is_read = TRUE
            WHERE user_id = %s
            """,
            (user_id,),
        )
    conn.commit()
    cur.close()
    conn.close()