from pydantic import BaseModel, Field


class CreateBookingRequest(BaseModel):
    event_id: int
    quantity: int = Field(gt=0)
