from pydantic import BaseModel, Field


class CaseCreateRequest(BaseModel):
    client_id: int
    title: str = Field(..., min_length=1, max_length=200)
    description: str = Field(..., min_length=1, max_length=5000)
    legal_area: str | None = Field(None, max_length=200)
    issue_type: str | None = Field(None, max_length=200)
    ai_summary: str | None = Field(None, max_length=5000)
    urgency: str | None = Field(None, max_length=50)
    city: str | None = Field(None, max_length=200)
    case_brief: dict | None = None
    status: str = Field("open", max_length=20)
    publish_publicly: bool = True


class CaseApplyRequest(BaseModel):
    case_id: int
    lawyer_id: int
    message: str = Field(..., max_length=5000)
    status: str = Field("submitted", max_length=50)


class CaseEventRequest(BaseModel):
    description: str = Field(..., min_length=1, max_length=2000)
    event_date: str


class CaseApplicationDecisionRequest(BaseModel):
    client_id: int
    decision: str = Field(..., max_length=20)


class CaseCloseRequest(BaseModel):
    client_id: int
    reason: str | None = Field(None, max_length=2000)
