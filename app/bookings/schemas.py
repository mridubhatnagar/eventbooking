from pydantic import BaseModel, Field


class CreateBookingRequest(BaseModel):
    event_id: int
    quantity: int = Field(gt=0)


class ListBookingsQuery(BaseModel):
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)
