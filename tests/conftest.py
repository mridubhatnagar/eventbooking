import os

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
def mock_app():
    from mock_razorpay_app import create_mock_app

    application = create_mock_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture
def mock_client(mock_app):
    return mock_app.test_client()
