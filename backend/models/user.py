from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=254)
    password: str = Field(..., min_length=1, max_length=256)


class SignupRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=100)
    password: str = Field(..., min_length=1, max_length=256)
    # Optional so older deployed frontend builds that don't send it yet keep
    # working (fall back to the placeholder) - see routers/auth.py::signup.
    email: EmailStr | None = None
    role: str = "client"
