from typing import Annotated

from fastapi import APIRouter, Query

from models.notification import NotificationReadRequest
from services.notification_service import get_notifications, mark_notifications_read

router = APIRouter(tags=["notifications"])


@router.get("/notifications")
async def list_notifications(user_id: Annotated[int, Query()]):
    items = get_notifications(user_id)
    unread_count = sum(1 for item in items if not item["is_read"])
    return {"items": items, "unread_count": unread_count}


@router.post("/notifications/read")
async def read_notifications(data: NotificationReadRequest):
    mark_notifications_read(data.user_id, data.notification_ids)
    return {"success": True}