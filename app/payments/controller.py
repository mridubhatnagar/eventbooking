from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError
import requests

from app.decorators import api_key_required
from app.payments.service import PaymentService
from app.payments.schemas import WebhookRequest
from app.payments.signature import compute_signature, verify_signature
from app.docs import api

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
        return jsonify({"error": "invalid signature"}), 401

    data = request.context.json

    try:
        payment_service.process_webhook_event(data.order_id, data.event)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"status": "ok"}), 200


@bp.post("/mock/razorpay/simulate-webhook")
@api_key_required
def simulate_webhook():
    """Throwaway mock — stands in for Razorpay's servers. Builds a fake
    signed event and calls the real webhook receiver via an actual HTTP
    request, exercising the same code path a real integration would hit.
    Deliberately undecorated by @api.validate (spectree mode="strict") so
    it never appears in the public OpenAPI/Swagger docs."""
    try:
        data = WebhookRequest.model_validate(request.get_json(force=True))
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    body_bytes = data.model_dump_json().encode()
    secret = current_app.config["RAZORPAY_WEBHOOK_SECRET"]
    signature = compute_signature(body_bytes, secret)

    response = requests.post(
        f"{current_app.config['WEB_BASE_URL']}/webhooks/razorpay",
        data=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
        timeout=10,
    )

    return jsonify({"webhook_status": response.status_code}), 200
