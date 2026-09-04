from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.enums import Industry
from app.timezone import now_ist


def _reject_timezone_offset(value: datetime | None) -> datetime | None:
    """All dates are assumed IST (see app/timezone.py) — a date with an
    explicit offset is rejected with a clean 400 rather than converted,
    since the API only ever documents/sends naive dates."""
    if value is not None and value.tzinfo is not None:
        raise ValueError("date must not include a timezone offset — IST is assumed")
    return value


def _reject_past_date(value: datetime | None) -> datetime | None:
    value = _reject_timezone_offset(value)
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

    _reject_date_from_offset = field_validator("date_from")(_reject_timezone_offset)
    _reject_date_to_offset = field_validator("date_to")(_reject_timezone_offset)
