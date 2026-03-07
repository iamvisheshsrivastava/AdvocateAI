from pydantic import BaseModel


class LawyerProfileRequest(BaseModel):
    lawyer_id: int
    name: str
    city: str = ""
    practice_areas: list[str] | str = []
    languages: list[str] | str = []
    experience_years: int = 0
    rating: float = 0
    bio: str = ""
    availability_status: str = "available"


class WatchlistRequest(BaseModel):
    user_id: int
    professional_ids: list[int]
