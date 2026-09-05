import re

from pydantic import BaseModel, Field, field_validator

from app.enums import Industry

# Standard Indian govt/banking ID formats.
PAN_PATTERN = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
GST_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$")
IFSC_PATTERN = re.compile(r"^[A-Z]{4}0[A-Z0-9]{6}$")
BANK_ACCOUNT_PATTERN = re.compile(r"^[0-9]{9,18}$")


def _validate_pan(value: str | None) -> str | None:
    if value is None:
        return value
    value = value.strip().upper()
    if not PAN_PATTERN.match(value):
        raise ValueError("pan_number must match the format AAAAA9999A")
    return value


def _validate_gst(value: str | None) -> str | None:
    if value is None:
        return value
    value = value.strip().upper()
    if not GST_PATTERN.match(value):
        raise ValueError("gst_number must be a valid 15-character GSTIN")
    return value


def _validate_ifsc(value: str | None) -> str | None:
    if value is None:
        return value
    value = value.strip().upper()
    if not IFSC_PATTERN.match(value):
        raise ValueError("bank_ifsc_code must match the format AAAA0XXXXXX")
    return value


def _validate_bank_account_number(value: str | None) -> str | None:
    if value is None:
        return value
    value = value.strip()
    if not BANK_ACCOUNT_PATTERN.match(value):
        raise ValueError("bank_account_number must be 9-18 digits")
    return value


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

    _validate_pan_number = field_validator("pan_number")(_validate_pan)
    _validate_gst_number = field_validator("gst_number")(_validate_gst)
    _validate_bank_ifsc_code = field_validator("bank_ifsc_code")(_validate_ifsc)
    _validate_bank_account_number = field_validator("bank_account_number")(
        _validate_bank_account_number
    )


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

    _validate_pan_number = field_validator("pan_number")(_validate_pan)
    _validate_gst_number = field_validator("gst_number")(_validate_gst)
    _validate_bank_ifsc_code = field_validator("bank_ifsc_code")(_validate_ifsc)
    _validate_bank_account_number = field_validator("bank_account_number")(
        _validate_bank_account_number
    )
