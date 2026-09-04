from pydantic import BaseModel, Field

from app.enums import Industry


class OrganizerProfileFields(BaseModel):
    company_name: str = Field(min_length=1)
    city: str = Field(min_length=1)
    address: str = Field(min_length=1)
    industry: Industry
    gst_number: str | None = None
    pan_number: str = Field(min_length=1)
    bank_account_holder_name: str = Field(min_length=1)
    bank_account_number: str = Field(min_length=1)
    bank_ifsc_code: str = Field(min_length=1)
    bank_name: str = Field(min_length=1)


class UpdateOrganizerProfileRequest(BaseModel):
    company_name: str | None = Field(default=None, min_length=1)
    city: str | None = Field(default=None, min_length=1)
    address: str | None = Field(default=None, min_length=1)
    industry: Industry | None = None
    gst_number: str | None = None
    pan_number: str | None = Field(default=None, min_length=1)
    bank_account_holder_name: str | None = Field(default=None, min_length=1)
    bank_account_number: str | None = Field(default=None, min_length=1)
    bank_ifsc_code: str | None = Field(default=None, min_length=1)
    bank_name: str | None = Field(default=None, min_length=1)
