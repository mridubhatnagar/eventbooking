from pydantic import BaseModel, EmailStr, Field, model_validator

from app.enums import Role
from app.organizer_profiles.schemas import OrganizerProfileFields


class RegisterRequest(BaseModel):
    email: EmailStr
    phone: str | None = None
    password: str = Field(min_length=8)
    role: Role
    # Required when role == organizer (see validator below); rejected for customers.
    organizer_profile: OrganizerProfileFields | None = None

    @model_validator(mode="after")
    def _organizer_profile_matches_role(self):
        if self.role == Role.ORGANIZER and self.organizer_profile is None:
            raise ValueError("organizer_profile is required when role is organizer")
        if self.role != Role.ORGANIZER and self.organizer_profile is not None:
            raise ValueError("organizer_profile is only allowed when role is organizer")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)
