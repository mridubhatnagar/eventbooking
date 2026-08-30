from flask import Blueprint, current_app, request

from app.payments.service import PaymentService
from app.payments.schemas import WebhookRequest
from app.payments.signature import verify_signature
from app.docs import api
from app.responses import success, error

bp = Blueprint("payments", __name__)
payment_service = PaymentService()


@bp.post("/webhooks/razorpay")
@api.validate(json=WebhookRequest, tags=["payments"])
def razorpay_webhook():
    """Real webhook receiver — genuine, reusable code. Signature-verified,
    not JWT (mirrors how real gateway webhooks are secured)."""
    raw_body = request.get_data()
    signature = request.headers.get("X-Razorpay-Signature")

    if not verify_signature(
        raw_body, signature, current_app.config["RAZORPAY_WEBHOOK_SECRET"]
    ):
        return error("invalid signature", 401)

    data = request.context.json

    try:
        payment_service.process_webhook_event(data.order_id, data.event)
    except ValueError as e:
        return error(str(e), 400)

    return success({"status": "ok"}, 200)
