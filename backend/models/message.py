from pydantic import BaseModel, Field


class MessageSendRequest(BaseModel):
    case_id: int
    sender_id: int
    receiver_id: int
    content: str = Field(..., min_length=1, max_length=5000)
