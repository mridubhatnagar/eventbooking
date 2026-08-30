from pydantic import BaseModel, Field

from app.enums import Role


class RegisterRequest(BaseModel):
    email: str = Field(min_length=1)
    phone: str | None = None
    password: str = Field(min_length=1)
    role: Role


class LoginRequest(BaseModel):
    email: str = Field(min_length=1)
    password: str = Field(min_length=1)
