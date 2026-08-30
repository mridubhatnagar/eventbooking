import pytest

from app.payments.service import PaymentService
from app.payments.signature import compute_signature, verify_signature
from app.bookings.tasks import send_booking_confirmation
from app.exceptions import TaskEnqueueError


@pytest.fixture
def payment_service(fake_payment_repo):
    return PaymentService(payment_repository=fake_payment_repo)


def _seed_payment(fake_payment_repo, order_id="order-1"):
    return fake_payment_repo.create(
        booking_id=1,
        amount=100,
        order_id=order_id,
        gateway_status="created",
        status="PENDING",
    )


class TestProcessWebhookEvent:
    def test_captured_event_marks_processed(
        self, app, payment_service, fake_payment_repo, monkeypatch
    ):
        monkeypatch.setattr(send_booking_confirmation, "delay", lambda *a, **kw: None)
        payment = _seed_payment(fake_payment_repo)

        with app.app_context():
            updated = payment_service.process_webhook_event(
                payment.order_id, "payment.captured"
            )

        assert updated.status == "PROCESSED"
        assert updated.gateway_status == "captured"

    def test_failed_event_marks_failed(self, app, payment_service, fake_payment_repo):
        payment = _seed_payment(fake_payment_repo)

        with app.app_context():
            updated = payment_service.process_webhook_event(
                payment.order_id, "payment.failed"
            )

        assert updated.status == "FAILED"
        assert updated.gateway_status == "failed"

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
            payment_service.process_webhook_event(payment.order_id, "payment.captured")

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
            payment_service.process_webhook_event(payment.order_id, "payment.failed")

        assert calls == []

    def test_unknown_order_id_raises(self, app, payment_service):
        with app.app_context(), pytest.raises(ValueError, match="not found"):
            payment_service.process_webhook_event(
                "nonexistent-order", "payment.captured"
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
            payment_service.process_webhook_event(payment.order_id, "payment.captured")


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
