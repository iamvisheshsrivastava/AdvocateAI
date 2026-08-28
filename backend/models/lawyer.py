from pydantic import BaseModel, Field


class LawyerProfileRequest(BaseModel):
    lawyer_id: int
    name: str = Field(..., min_length=1, max_length=200)
    city: str = Field("", max_length=200)
    practice_areas: list[str] | str = []
    languages: list[str] | str = []
    experience_years: int = Field(0, ge=0, le=100)
    rating: float = Field(0, ge=0, le=5)
    bio: str = Field("", max_length=3000)
    availability_status: str = Field("available", max_length=50)


class WatchlistRequest(BaseModel):
    user_id: int
    professional_ids: list[int] = Field(..., max_length=500)
