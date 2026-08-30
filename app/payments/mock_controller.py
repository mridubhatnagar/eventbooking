"""Mock Razorpay API — impersonates Razorpay's own servers, not our API.
Deliberately runs as a separate service (mock_razorpay_app.py) from the real
app, not just a separate blueprint: our app genuinely calls out over the
network to create/capture orders, exactly like it would call the real
Razorpay API, so this has to be a different process — otherwise a single
gunicorn worker ends up both the caller and the callee of its own request."""

import uuid

from flask import Blueprint, current_app, jsonify, request
from pydantic import ValidationError
import requests

from app.decorators import api_key_required
from app.payments.schemas import WebhookRequest
from app.payments.signature import compute_signature
from app.enums import GatewayStatus

bp = Blueprint("mock_razorpay", __name__)


def _key_auth_failed():
    """Basic Auth check shared by the mock Orders/Payments endpoints —
    mirrors how a real Razorpay REST endpoint authenticates key_id/key_secret."""
    auth = request.authorization
    expected_id = current_app.config["RAZORPAY_KEY_ID"]
    expected_secret = current_app.config["RAZORPAY_KEY_SECRET"]
    return (
        not auth
        or not expected_id
        or auth.username != expected_id
        or auth.password != expected_secret
    )


@bp.post("/mock/razorpay/orders")
def mock_create_order():
    """Stands in for Razorpay's real Orders API (POST /v1/orders).
    Authenticated the same way a real Razorpay SDK would authenticate
    itself: HTTP Basic Auth with key_id/key_secret. Response shape mirrors
    Razorpay's real Orders API response, since calling code stands in for
    a real razorpay-python client call."""
    if _key_auth_failed():
        return (
            jsonify(
                {
                    "error": {
                        "code": "BAD_REQUEST_ERROR",
                        "description": "Authentication failed",
                    }
                }
            ),
            401,
        )

    body = request.get_json(force=True, silent=True) or {}
    return (
        jsonify(
            {
                "id": f"order_{uuid.uuid4().hex[:14]}",
                "amount": body.get("amount"),
                "currency": body.get("currency", "INR"),
                "status": GatewayStatus.CREATED,
            }
        ),
        200,
    )


@bp.post("/mock/razorpay/payments/capture")
def mock_capture_payment():
    """Stands in for Razorpay's real Payment Capture API
    (POST /v1/payments/:id/capture). Same Basic Auth scheme as
    /mock/razorpay/orders — every real Razorpay REST endpoint uses the same
    key_id/key_secret credentials, not just order creation."""
    if _key_auth_failed():
        return (
            jsonify(
                {
                    "error": {
                        "code": "BAD_REQUEST_ERROR",
                        "description": "Authentication failed",
                    }
                }
            ),
            401,
        )

    body = request.get_json(force=True, silent=True) or {}
    return (
        jsonify(
            {
                "id": f"pay_{uuid.uuid4().hex[:14]}",
                "order_id": body.get("order_id"),
                "status": GatewayStatus.CAPTURED,
            }
        ),
        200,
    )


@bp.post("/mock/razorpay/simulate-webhook")
@api_key_required
def simulate_webhook():
    """Stands in for Razorpay's servers delivering a webhook. Builds a fake
    signed event and calls the real app's webhook receiver via an actual
    HTTP request, exercising the same code path a real integration would hit."""
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
