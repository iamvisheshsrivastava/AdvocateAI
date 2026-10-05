from pydantic import BaseModel, Field


class CreateCheckoutSessionRequest(BaseModel):
    user_id: int
    plan: str = Field(..., max_length=50)
    success_url: str = Field(..., max_length=1000)
    cancel_url: str = Field(..., max_length=1000)
