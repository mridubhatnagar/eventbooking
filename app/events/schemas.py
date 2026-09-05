from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator

from app.enums import Industry, Meridiem
from app.timezone import now_ist


def _combine(event_date: date, hour: int, minute: int, meridiem: Meridiem) -> datetime:
    """Organizers aren't developers — they pick a date, an hour/minute, and
    AM/PM, not an ISO datetime string with a timezone offset. Timezone isn't
    asked for at all: it's pre-populated as IST (see app/timezone.py)."""
    hour_24 = hour % 12
    if meridiem == Meridiem.PM:
        hour_24 += 12
    return datetime.combine(event_date, time(hour_24, minute))


class CreateEventRequest(BaseModel):
    name: str = Field(min_length=1)
    event_date: date
    hour: int = Field(ge=1, le=12)
    minute: int = Field(ge=0, le=59)
    meridiem: Meridiem
    venue: str = Field(min_length=1)
    city: str = Field(min_length=1)
    capacity: int = Field(gt=0)
    price: Decimal = Field(ge=0)

    @property
    def date(self) -> datetime:
        return _combine(self.event_date, self.hour, self.minute, self.meridiem)

    @model_validator(mode="after")
    def _reject_past_date(self):
        if self.date <= now_ist():
            raise ValueError("date must be in the future")
        return self


class UpdateEventRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    event_date: date | None = None
    hour: int | None = Field(default=None, ge=1, le=12)
    minute: int | None = Field(default=None, ge=0, le=59)
    meridiem: Meridiem | None = None
    venue: str | None = Field(default=None, min_length=1)
    city: str | None = Field(default=None, min_length=1)
    capacity: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0)

    @property
    def date(self) -> datetime | None:
        if self.event_date is None:
            return None
        return _combine(self.event_date, self.hour, self.minute, self.meridiem)

    @model_validator(mode="after")
    def _validate_date_time_group(self):
        parts = (self.event_date, self.hour, self.minute, self.meridiem)
        provided = [p is not None for p in parts]
        if any(provided) and not all(provided):
            raise ValueError(
                "event_date, hour, minute, and meridiem must all be provided together"
            )
        if self.event_date is not None and self.date <= now_ist():
            raise ValueError("date must be in the future")
        return self


class ListEventsQuery(BaseModel):
    city: str | None = Field(default=None, min_length=1)
    date_from: date | None = None
    date_to: date | None = None
    industry: Industry | None = None
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
