from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.enums import Industry


def _reject_past_date(value: datetime | None) -> datetime | None:
    if value is not None and value <= datetime.now(timezone.utc).replace(tzinfo=None):
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
