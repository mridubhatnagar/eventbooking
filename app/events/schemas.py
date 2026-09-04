from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class CreateEventRequest(BaseModel):
    name: str = Field(min_length=1)
    date: datetime
    venue: str = Field(min_length=1)
    city: str = Field(min_length=1)
    capacity: int = Field(gt=0)
    price: Decimal = Field(ge=0)


class UpdateEventRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1)
    date: datetime | None = None
    venue: str | None = Field(default=None, min_length=1)
    city: str | None = Field(default=None, min_length=1)
    capacity: int | None = Field(default=None, gt=0)
    price: Decimal | None = Field(default=None, ge=0)


class ListEventsQuery(BaseModel):
    city: str | None = Field(default=None, min_length=1)
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
