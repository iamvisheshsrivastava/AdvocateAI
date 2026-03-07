from pydantic import BaseModel


class CaseCreateRequest(BaseModel):
    client_id: int
    title: str
    description: str
    legal_area: str | None = None
    issue_type: str | None = None
    ai_summary: str | None = None
    urgency: str | None = None
    city: str | None = None
    status: str = "open"
    publish_publicly: bool = True


class CaseApplyRequest(BaseModel):
    case_id: int
    lawyer_id: int
    message: str
    status: str = "submitted"
