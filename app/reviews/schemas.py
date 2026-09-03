from pydantic import BaseModel, Field


class CreateReviewRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    review_text: str | None = Field(default=None, min_length=1)
