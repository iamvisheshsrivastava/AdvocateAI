from pydantic import BaseModel


class MessageSendRequest(BaseModel):
    case_id: int
    sender_id: int
    receiver_id: int
    content: str