from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from auth_utils import get_current_user
from models.notification import NotificationReadRequest
from services.notification_service import get_notifications, mark_notifications_read
from logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["notifications"])


def _require_self(current_user: dict, user_id: int, message: str) -> None:
    """Raise 403 unless the authenticated caller's JWT subject matches user_id."""
    if str(current_user.get("sub")) != str(user_id):
        raise HTTPException(status_code=403, detail=message)


@router.get("/notifications")
async def list_notifications(
    user_id: Annotated[int, Query()],
    current_user: dict = Depends(get_current_user),
):
    _require_self(current_user, user_id, "You can only view your own notifications.")
    try:
        items = get_notifications(user_id)
        unread_count = sum(1 for item in items if not item["is_read"])
        return {"items": items, "unread_count": unread_count}
    except Exception:
        logger.exception("Failed to list notifications for user_id=%s", user_id)
        return {"items": [], "unread_count": 0}


@router.post("/notifications/read")
async def read_notifications(
    data: NotificationReadRequest,
    current_user: dict = Depends(get_current_user),
):
    _require_self(current_user, data.user_id, "You can only modify your own notifications.")
    try:
        mark_notifications_read(data.user_id, data.notification_ids)
        return {"success": True}
    except Exception:
        logger.exception("Failed to mark notifications read for user_id=%s", data.user_id)
        return {"success": False}