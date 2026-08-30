from pydantic import BaseModel

from app.enums import WebhookEvent


class WebhookRequest(BaseModel):
    order_id: str
    event: WebhookEvent
