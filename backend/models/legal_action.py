from pydantic import BaseModel


class LegalActionGuideRequest(BaseModel):
    problem_description: str
