from pydantic import BaseModel


class DocumentQuestionRequest(BaseModel):
    document_batch_id: str
    question: str
    user_id: int | None = None
