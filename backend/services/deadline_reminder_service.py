"""Proactive deadline reminder scan (issue #22).

Walks active (open) cases, recomputes deadlines via the existing
``case_intelligence_service`` extraction helpers, and fires a notification
through the existing notification/realtime plumbing the first time a
deadline crosses a threshold (7/3/1 days out, or newly overdue). Already
notified (case, deadline, threshold) triples are recorded in
``deadline_reminders_sent`` so re-running the scan never spams the user.
"""
from __future__ import annotations

from typing import Any

from db.database import get_db_connection
from logging_config import get_logger
from services.case_intelligence_service import _extract_deadlines
from services.notification_service import create_notification

logger = get_logger(__name__)


def _fetch_active_cases() -> list[tuple]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT case_id, client_id, title, description, legal_area, issue_type,
               ai_summary, urgency, city, case_brief
        FROM cases
        WHERE status = 'open'
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def _fetch_timeline_events(case_id: int) -> list[dict[str, Any]]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, description, event_date, created_at FROM case_events WHERE case_id = %s",
        (case_id,),
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        {"id": r[0], "description": r[1], "event_date": str(r[2]), "created_at": str(r[3])}
        for r in rows
    ]


def _mark_sent_if_new(case_id: int, deadline_key: str, threshold: str) -> bool:
    """Record (case_id, deadline_key, threshold) and return True iff it was new."""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO deadline_reminders_sent (case_id, deadline_key, threshold)
        VALUES (%s, %s, %s)
        ON CONFLICT (case_id, deadline_key, threshold) DO NOTHING
        RETURNING id
        """,
        (case_id, deadline_key, threshold),
    )
    inserted = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    return inserted is not None


def _threshold_for(days_until: int) -> str | None:
    if days_until < 0:
        return "overdue"
    if days_until <= 1:
        return "1_day"
    if days_until <= 3:
        return "3_day"
    if days_until <= 7:
        return "7_day"
    return None


def scan_and_notify_deadlines() -> int:
    """Scan all open cases and notify on newly-crossed deadline thresholds.

    Returns the number of notifications actually sent (0 if nothing new).
    """
    notifications_sent = 0
    for row in _fetch_active_cases():
        (
            case_id,
            client_id,
            title,
            description,
            legal_area,
            issue_type,
            ai_summary,
            urgency,
            city,
            case_brief,
        ) = row
        analysis = {
            "legal_area": legal_area,
            "issue_type": issue_type,
            "summary": ai_summary or description,
            "urgency": urgency,
            "location": city,
        }
        try:
            timeline_events = _fetch_timeline_events(case_id)
            deadlines = _extract_deadlines(case_brief or {}, timeline_events, analysis)
        except Exception:
            logger.exception("Failed to extract deadlines for case %s", case_id)
            continue

        for deadline in deadlines:
            threshold = _threshold_for(deadline["days_until"])
            if threshold is None:
                continue
            deadline_key = f"{deadline['date']}::{deadline['title']}"
            try:
                is_new = _mark_sent_if_new(case_id, deadline_key, threshold)
            except Exception:
                logger.exception("Failed to record deadline reminder state for case %s", case_id)
                continue
            if not is_new:
                continue

            if threshold == "overdue":
                message = f"Deadline overdue on case #{case_id}: {deadline['title']} ({deadline['date']})."
            else:
                message = f"Deadline approaching on case #{case_id}: {deadline['title']} ({deadline['date']})."

            try:
                create_notification(
                    user_id=client_id,
                    message=message,
                    notification_type="deadline_reminder",
                )
                notifications_sent += 1
            except Exception:
                logger.exception("Failed to send deadline reminder notification for case %s", case_id)

    return notifications_sent
