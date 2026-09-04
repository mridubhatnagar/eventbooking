import os
import uuid

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-32-bytes-minimum-xxxx")
os.environ.setdefault("RAZORPAY_WEBHOOK_SECRET", "test-webhook-secret")
os.environ.setdefault("MOCK_TRIGGER_API_KEY", "test-api-key")

from tests.fakes import (
    FakeUserRepository,
    FakeEventRepository,
    FakeBookingRepository,
    FakePaymentRepository,
    FakeOrganizerProfileRepository,
    FakeReviewRepository,
)


@pytest.fixture
def fake_user_repo():
    return FakeUserRepository()


@pytest.fixture
def fake_event_repo():
    return FakeEventRepository()


@pytest.fixture
def fake_booking_repo():
    return FakeBookingRepository()


@pytest.fixture
def fake_payment_repo():
    return FakePaymentRepository()


@pytest.fixture
def fake_organizer_profile_repo():
    return FakeOrganizerProfileRepository()


@pytest.fixture
def fake_review_repo():
    return FakeReviewRepository()


@pytest.fixture
def app():
    from app import create_app
    from app.extensions import db

    application = create_app()
    application.config["TESTING"] = True
    with application.app_context():
        db.create_all()
    return application


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def register_and_login(client):
    """Registers + logs in a fresh user via the real HTTP endpoints and
    returns (user_id, auth_headers) — for controller-level tests that need
    a real JWT rather than a fake identity."""

    def _do(role, password="pw123456"):
        from app.enums import Role

        email = f"user-{uuid.uuid4().hex[:8]}@test.com"
        payload = {
            "email": email,
            "phone": "555-0000",
            "password": password,
            "role": role,
        }
        if role == Role.ORGANIZER:
            payload["organizer_profile"] = {
                "company_name": "Test Events Co",
                "city": "Bengaluru",
                "address": "123 Test Street, Bengaluru",
                "industry": "MUSIC",
                "pan_number": "ABCDE1234F",
                "bank_account_holder_name": "Test Events Co",
                "bank_account_number": "000123456789",
                "bank_ifsc_code": "TEST0001234",
                "bank_name": "Test Bank",
            }
        resp = client.post("/auth/register", json=payload)
        assert resp.status_code == 201, resp.get_json()
        user_id = resp.get_json()["data"]["id"]

        resp = client.post("/auth/login", json={"email": email, "password": password})
        assert resp.status_code == 200, resp.get_json()
        token = resp.get_json()["data"]["access_token"]

        return user_id, {"Authorization": f"Bearer {token}"}

    return _do


@pytest.fixture
def mock_app():
    from mock_razorpay_app import create_mock_app

    application = create_mock_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def mock_client(mock_app):
    return mock_app.test_client()
