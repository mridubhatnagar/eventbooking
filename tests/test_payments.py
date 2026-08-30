import base64

import pytest
import requests

from app.payments.service import PaymentService
from app.payments.signature import compute_signature, verify_signature
from app.payments.gateway_client import create_order, capture_payment
from app.bookings.tasks import send_booking_confirmation
from app.exceptions import GatewayError, TaskEnqueueError
from app.enums import GatewayStatus, JobStatus, PaymentStatus, WebhookEvent


@pytest.fixture
def payment_service(fake_payment_repo):
    return PaymentService(payment_repository=fake_payment_repo)


def _seed_payment(fake_payment_repo, order_id="order-1"):
    return fake_payment_repo.create(
        booking_id=1,
        amount=100,
        order_id=order_id,
        gateway_status=GatewayStatus.CREATED,
        status=PaymentStatus.PENDING,
    )


class TestProcessWebhookEvent:
    def test_captured_event_marks_processed(
        self, app, payment_service, fake_payment_repo, monkeypatch
    ):
        monkeypatch.setattr(send_booking_confirmation, "delay", lambda *a, **kw: None)
        payment = _seed_payment(fake_payment_repo)

        with app.app_context():
            updated = payment_service.process_webhook_event(
                payment.order_id, WebhookEvent.PAYMENT_CAPTURED
            )

        assert updated.status == PaymentStatus.PROCESSED
        assert updated.gateway_status == GatewayStatus.CAPTURED

    def test_failed_event_marks_failed(self, app, payment_service, fake_payment_repo):
        payment = _seed_payment(fake_payment_repo)

        with app.app_context():
            updated = payment_service.process_webhook_event(
                payment.order_id, WebhookEvent.PAYMENT_FAILED
            )

        assert updated.status == PaymentStatus.FAILED
        assert updated.gateway_status == GatewayStatus.FAILED

    def test_captured_triggers_confirmation_task(
        self, app, payment_service, fake_payment_repo, monkeypatch
    ):
        calls = []
        monkeypatch.setattr(
            send_booking_confirmation,
            "delay",
            lambda booking_id, payment_id=None: calls.append((booking_id, payment_id)),
        )
        payment = _seed_payment(fake_payment_repo)

        with app.app_context():
            payment_service.process_webhook_event(
                payment.order_id, WebhookEvent.PAYMENT_CAPTURED
            )

        assert calls == [(payment.booking_id, payment.id)]

    def test_failed_does_not_trigger_confirmation_task(
        self, app, payment_service, fake_payment_repo, monkeypatch
    ):
        calls = []
        monkeypatch.setattr(
            send_booking_confirmation, "delay", lambda *a, **kw: calls.append(1)
        )
        payment = _seed_payment(fake_payment_repo)

        with app.app_context():
            payment_service.process_webhook_event(
                payment.order_id, WebhookEvent.PAYMENT_FAILED
            )

        assert calls == []

    def test_unknown_order_id_raises(self, app, payment_service):
        with app.app_context(), pytest.raises(ValueError, match="not found"):
            payment_service.process_webhook_event(
                "nonexistent-order", WebhookEvent.PAYMENT_CAPTURED
            )

    def test_unknown_event_type_raises(self, app, payment_service, fake_payment_repo):
        payment = _seed_payment(fake_payment_repo)

        with app.app_context(), pytest.raises(ValueError, match="unknown event type"):
            payment_service.process_webhook_event(payment.order_id, "payment.refunded")

    def test_broker_failure_raises_task_enqueue_error(
        self, app, payment_service, fake_payment_repo, monkeypatch
    ):
        monkeypatch.setattr(
            send_booking_confirmation,
            "delay",
            lambda *a, **kw: (_ for _ in ()).throw(ConnectionError("broker down")),
        )
        payment = _seed_payment(fake_payment_repo)

        with app.app_context(), pytest.raises(TaskEnqueueError):
            payment_service.process_webhook_event(
                payment.order_id, WebhookEvent.PAYMENT_CAPTURED
            )


class TestSignature:
    def test_valid_signature_verifies(self):
        body = b'{"order_id":"abc","event":"payment.captured"}'
        secret = "my-secret"
        signature = compute_signature(body, secret)

        assert verify_signature(body, signature, secret) is True

    def test_tampered_body_fails_verification(self):
        body = b'{"order_id":"abc","event":"payment.captured"}'
        secret = "my-secret"
        signature = compute_signature(body, secret)

        tampered_body = b'{"order_id":"xyz","event":"payment.captured"}'
        assert verify_signature(tampered_body, signature, secret) is False

    def test_wrong_secret_fails_verification(self):
        body = b'{"order_id":"abc","event":"payment.captured"}'
        signature = compute_signature(body, "correct-secret")

        assert verify_signature(body, signature, "wrong-secret") is False

    @pytest.mark.parametrize("bad_signature", [None, "", "not-a-real-signature"])
    def test_missing_or_invalid_signature_fails(self, bad_signature):
        body = b'{"order_id":"abc","event":"payment.captured"}'

        assert verify_signature(body, bad_signature, "any-secret") is False


class TestMockCreateOrderEndpoint:
    """These endpoints live on the separate mock-razorpay service
    (mock_razorpay_app.py), not the main app — see app/payments/mock_controller.py."""

    def _auth_header(self, key_id, key_secret):
        token = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def test_missing_auth_returns_401(self, mock_app, mock_client):
        mock_app.config["RAZORPAY_KEY_ID"] = "test_key_id"
        mock_app.config["RAZORPAY_KEY_SECRET"] = "test_key_secret"

        response = mock_client.post("/mock/razorpay/orders", json={"amount": "10.00"})

        assert response.status_code == 401

    def test_wrong_credentials_returns_401(self, mock_app, mock_client):
        mock_app.config["RAZORPAY_KEY_ID"] = "test_key_id"
        mock_app.config["RAZORPAY_KEY_SECRET"] = "test_key_secret"

        response = mock_client.post(
            "/mock/razorpay/orders",
            json={"amount": "10.00"},
            headers=self._auth_header("test_key_id", "wrong_secret"),
        )

        assert response.status_code == 401

    def test_valid_credentials_returns_order(self, mock_app, mock_client):
        mock_app.config["RAZORPAY_KEY_ID"] = "test_key_id"
        mock_app.config["RAZORPAY_KEY_SECRET"] = "test_key_secret"

        response = mock_client.post(
            "/mock/razorpay/orders",
            json={"amount": "10.00", "currency": "INR"},
            headers=self._auth_header("test_key_id", "test_key_secret"),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["id"].startswith("order_")
        assert body["amount"] == "10.00"
        assert body["status"] == GatewayStatus.CREATED


class TestMockCapturePaymentEndpoint:
    def _auth_header(self, key_id, key_secret):
        token = base64.b64encode(f"{key_id}:{key_secret}".encode()).decode()
        return {"Authorization": f"Basic {token}"}

    def test_missing_auth_returns_401(self, mock_app, mock_client):
        mock_app.config["RAZORPAY_KEY_ID"] = "test_key_id"
        mock_app.config["RAZORPAY_KEY_SECRET"] = "test_key_secret"

        response = mock_client.post(
            "/mock/razorpay/payments/capture", json={"order_id": "order-1"}
        )

        assert response.status_code == 401

    def test_wrong_credentials_returns_401(self, mock_app, mock_client):
        mock_app.config["RAZORPAY_KEY_ID"] = "test_key_id"
        mock_app.config["RAZORPAY_KEY_SECRET"] = "test_key_secret"

        response = mock_client.post(
            "/mock/razorpay/payments/capture",
            json={"order_id": "order-1"},
            headers=self._auth_header("test_key_id", "wrong_secret"),
        )

        assert response.status_code == 401

    def test_valid_credentials_returns_captured_payment(self, mock_app, mock_client):
        mock_app.config["RAZORPAY_KEY_ID"] = "test_key_id"
        mock_app.config["RAZORPAY_KEY_SECRET"] = "test_key_secret"

        response = mock_client.post(
            "/mock/razorpay/payments/capture",
            json={"order_id": "order-1"},
            headers=self._auth_header("test_key_id", "test_key_secret"),
        )

        assert response.status_code == 200
        body = response.get_json()
        assert body["id"].startswith("pay_")
        assert body["order_id"] == "order-1"
        assert body["status"] == GatewayStatus.CAPTURED


class TestGatewayClient:
    def test_create_order_returns_id_on_success(self, app, monkeypatch):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"id": "order_abc123"}

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            assert create_order(100) == "order_abc123"

    def test_create_order_raises_gateway_error_on_request_failure(
        self, app, monkeypatch
    ):
        def _boom(*a, **kw):
            raise requests.ConnectionError("connection refused")

        monkeypatch.setattr(requests, "post", _boom)

        with app.app_context(), pytest.raises(GatewayError):
            create_order(100)

    def test_capture_payment_returns_id_on_success(self, app, monkeypatch):
        class FakeResponse:
            def raise_for_status(self):
                pass

            def json(self):
                return {"id": "pay_abc123"}

        monkeypatch.setattr(requests, "post", lambda *a, **kw: FakeResponse())

        with app.app_context():
            assert capture_payment("order-1") == "pay_abc123"

    def test_capture_payment_raises_gateway_error_on_request_failure(
        self, app, monkeypatch
    ):
        def _boom(*a, **kw):
            raise requests.ConnectionError("connection refused")

        monkeypatch.setattr(requests, "post", _boom)

        with app.app_context(), pytest.raises(GatewayError):
            capture_payment("order-1")


class TestRequestPaymentTask:
    def test_success_captures_and_schedules_callback(self, app, monkeypatch):
        from app.payments.repository import PaymentRepository
        from app.jobs.repository import JobRepository
        from app.payments.tasks import request_payment, trigger_gateway_callback

        monkeypatch.setattr(
            "app.payments.tasks.capture_payment", lambda order_id: "pay_test123"
        )
        calls = []
        monkeypatch.setattr(
            trigger_gateway_callback,
            "apply_async",
            lambda args=None, countdown=None: calls.append((args, countdown)),
        )

        with app.app_context():
            payment = PaymentRepository().create(
                booking_id=1,
                amount=100,
                order_id="order-xyz",
                gateway_status=GatewayStatus.CREATED,
                status=PaymentStatus.PENDING,
            )

            request_payment.apply(args=[payment.id])

            updated = PaymentRepository().get_by_id(payment.id)
            assert updated.status == PaymentStatus.REQUESTED
            assert updated.gateway_status == GatewayStatus.CAPTURED
            assert calls == [(["order-xyz", WebhookEvent.PAYMENT_CAPTURED], 5)]

            jobs = JobRepository().list(payment_id=payment.id)
            assert len(jobs) == 1
            assert jobs[0].status == JobStatus.SUCCESS

    def test_capture_failure_marks_job_failed_and_does_not_update_payment(
        self, app, monkeypatch
    ):
        from app.payments.repository import PaymentRepository
        from app.jobs.repository import JobRepository
        from app.payments.tasks import request_payment

        def _boom(order_id):
            raise GatewayError("gateway down")

        monkeypatch.setattr("app.payments.tasks.capture_payment", _boom)

        with app.app_context():
            payment = PaymentRepository().create(
                booking_id=1,
                amount=100,
                order_id="order-xyz",
                gateway_status=GatewayStatus.CREATED,
                status=PaymentStatus.PENDING,
            )

            result = request_payment.apply(args=[payment.id])
            assert result.failed()

            jobs = JobRepository().list(payment_id=payment.id)
            assert len(jobs) == 1
            assert jobs[0].status == JobStatus.FAILED

            unchanged = PaymentRepository().get_by_id(payment.id)
            assert unchanged.status == PaymentStatus.PENDING
            assert unchanged.gateway_status == GatewayStatus.CREATED
