from flask import current_app
import requests

from app.exceptions import GatewayError


def _key_auth():
    return (
        current_app.config["RAZORPAY_KEY_ID"],
        current_app.config["RAZORPAY_KEY_SECRET"],
    )


def create_order(amount):
    """Calls Razorpay's Orders API (mocked at POST /mock/razorpay/orders) to
    create an order, authenticated via HTTP Basic Auth with
    RAZORPAY_KEY_ID/RAZORPAY_KEY_SECRET — the same credentials a real
    razorpay-python client would use. Returns the gateway-issued order_id."""
    try:
        response = requests.post(
            f"{current_app.config['RAZORPAY_MOCK_BASE_URL']}/mock/razorpay/orders",
            json={"amount": str(amount), "currency": "INR"},
            auth=_key_auth(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["id"]
    except requests.RequestException as e:
        raise GatewayError(f"failed to create order with payment gateway: {e}") from e


def capture_payment(order_id):
    """Calls Razorpay's Payment Capture API (mocked at
    POST /mock/razorpay/payments/capture) to capture the payment for an
    order, authenticated the same way as create_order — every real Razorpay
    REST endpoint (Orders, Payments, Refunds, ...) uses the same key_id/
    key_secret Basic Auth, not just order creation."""
    try:
        response = requests.post(
            f"{current_app.config['RAZORPAY_MOCK_BASE_URL']}/mock/razorpay/payments/capture",
            json={"order_id": order_id},
            auth=_key_auth(),
            timeout=10,
        )
        response.raise_for_status()
        return response.json()["id"]
    except requests.RequestException as e:
        raise GatewayError(
            f"failed to capture payment with payment gateway: {e}"
        ) from e
