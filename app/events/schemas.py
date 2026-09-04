from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.enums import Industry
from app.timezone import now_ist, to_naive_ist


def _normalize_date(value: datetime | None) -> datetime | None:
    """Normalize any incoming datetime (aware or naive) to naive IST — so a
    client-sent offset (e.g. "+05:30") can never be compared against a naive
    `now` and crash, and stored/compared dates are consistently IST."""
    if value is not None:
        value = to_naive_ist(value)
    return value


def _reject_past_date(value: datetime | None) -> datetime | None:
    value = _normalize_date(value)
    if value is not None and value <= now_ist():
        raise ValueError("date must be in the future")
    return value


class CreateEventRequest(BaseModel):
    name: str = Field(min_length=1)
    date: datetime
    venue: str = Field(min_length=1)
    city: str = Field(min_length=1)
    capacity: int = Field(gt=0)
    price: Decimal = Field(ge=0)

    _validate_date = field_validator("date")(_reject_past_date)


class UpdateEventRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    date: datetime | None = None
    venue: str | None = Field(default=None, min_length=1)
    city: str | None = Field(default=None, min_length=1)
    capacity: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0)

    _validate_date = field_validator("date")(_reject_past_date)


class ListEventsQuery(BaseModel):
    city: str | None = Field(default=None, min_length=1)
    date_from: datetime | None = None
    date_to: datetime | None = None
    industry: Industry | None = None

    _normalize_date_from = field_validator("date_from")(_normalize_date)
    _normalize_date_to = field_validator("date_to")(_normalize_date)
