from pydantic import BaseModel

from app.enums import WebhookEvent


class TriggerWebhookRequest(BaseModel):
    """What the worker's trigger_gateway_callback task sends to the mock
    trigger endpoint — no payment_id yet, since Razorpay hasn't "processed"
    anything on our side until the mock mints it (see mock_controller.py)."""

    order_id: str
    event: WebhookEvent


class WebhookRequest(BaseModel):
    """What the real webhook receiver (POST /webhooks/razorpay) expects —
    mirrors a real Razorpay webhook payload, which always carries the
    gateway's own payment id alongside the order_id."""

    order_id: str
    event: WebhookEvent
    payment_id: str
