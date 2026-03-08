from pydantic import BaseModel


class NotificationReadRequest(BaseModel):
    user_id: int
    notification_ids: list[int] | None = None