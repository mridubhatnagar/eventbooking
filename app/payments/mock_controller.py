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
from app.payments.schemas import TriggerWebhookRequest, WebhookRequest
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


@bp.post("/mock/razorpay/simulate-webhook")
@api_key_required
def simulate_webhook():
    """Stands in for Razorpay's servers auto-capturing a payment and
    delivering the resulting webhook. Razorpay auto-captures by default (see
    decisions.md) — there is no separate merchant-initiated capture call, so
    this is the point where Razorpay's own payment id (pay_xxx) is minted,
    exactly as it would be internally on Razorpay's side during checkout.
    Builds a fake signed event carrying that id and calls the real app's
    webhook receiver via an actual HTTP request, exercising the same code
    path a real integration would hit."""
    try:
        data = TriggerWebhookRequest.model_validate(request.get_json(force=True))
    except ValidationError as e:
        return jsonify({"error": e.errors()}), 400

    webhook_payload = WebhookRequest(
        order_id=data.order_id,
        event=data.event,
        payment_id=f"pay_{uuid.uuid4().hex[:14]}",
    )

    body_bytes = webhook_payload.model_dump_json().encode()
    secret = current_app.config["RAZORPAY_WEBHOOK_SECRET"]
    signature = compute_signature(body_bytes, secret)

    response = requests.post(
        f"{current_app.config['WEB_BASE_URL']}/v1/webhooks/razorpay",
        data=body_bytes,
        headers={
            "Content-Type": "application/json",
            "X-Razorpay-Signature": signature,
        },
        timeout=10,
    )

    return jsonify({"webhook_status": response.status_code}), 200
