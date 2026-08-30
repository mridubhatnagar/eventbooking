from datetime import datetime
from decimal import Decimal

import pytest

from app.bookings.service import BookingService
from app.exceptions import TaskEnqueueError
from app.payments.tasks import request_payment


@pytest.fixture
def booking_service(fake_booking_repo, fake_event_repo, fake_payment_repo):
    return BookingService(
        booking_repository=fake_booking_repo,
        event_repository=fake_event_repo,
        payment_repository=fake_payment_repo,
    )


def _seed_event(fake_event_repo, capacity):
    return fake_event_repo.create(
        user_id=1,
        name="Concert",
        date=datetime(2026, 1, 1, 18, 0),
        venue="Hall A",
        city="Bengaluru",
        capacity=capacity,
        tickets_sold=0,
        price=Decimal("10.00"),
    )


class TestCreateBooking:
    @pytest.mark.parametrize(
        "capacity,quantity",
        [(10, 1), (10, 10), (1, 1)],  # exact fit included
    )
    def test_booking_succeeds_within_capacity(
        self, app, booking_service, fake_event_repo, monkeypatch, capacity, quantity
    ):
        monkeypatch.setattr(request_payment, "delay", lambda *a, **kw: None)
        monkeypatch.setattr(
            "app.bookings.service.create_order", lambda amount: "order_test123"
        )
        event = _seed_event(fake_event_repo, capacity)

        with app.app_context():
            booking, payment = booking_service.create_booking(
                user_id=5, event_id=event.id, quantity=quantity
            )

        assert booking.quantity == quantity
        assert payment.amount == Decimal("10.00") * quantity
        assert payment.status == "PENDING"
        assert fake_event_repo.get_by_id(event.id).tickets_sold == quantity

    @pytest.mark.parametrize("capacity,quantity", [(5, 6), (0, 1)])
    def test_booking_fails_over_capacity(
        self,
        app,
        booking_service,
        fake_event_repo,
        fake_booking_repo,
        monkeypatch,
        capacity,
        quantity,
    ):
        monkeypatch.setattr(request_payment, "delay", lambda *a, **kw: None)
        event = _seed_event(fake_event_repo, capacity)

        with app.app_context(), pytest.raises(ValueError, match="capacity"):
            booking_service.create_booking(
                user_id=5, event_id=event.id, quantity=quantity
            )

        assert fake_booking_repo.list() == []
        assert fake_event_repo.get_by_id(event.id).tickets_sold == 0

    def test_booking_nonexistent_event_raises(self, app, booking_service):
        with app.app_context(), pytest.raises(ValueError, match="not found"):
            booking_service.create_booking(user_id=5, event_id=999, quantity=1)

    @pytest.mark.parametrize("quantity", [0, -1])
    def test_booking_invalid_quantity_raises(
        self, app, booking_service, fake_event_repo, quantity
    ):
        event = _seed_event(fake_event_repo, capacity=10)

        with app.app_context(), pytest.raises(ValueError, match="quantity"):
            booking_service.create_booking(
                user_id=5, event_id=event.id, quantity=quantity
            )

    def test_broker_failure_raises_task_enqueue_error(
        self, app, booking_service, fake_event_repo, monkeypatch
    ):
        monkeypatch.setattr(
            request_payment,
            "delay",
            lambda *a, **kw: (_ for _ in ()).throw(ConnectionError("broker down")),
        )
        monkeypatch.setattr(
            "app.bookings.service.create_order", lambda amount: "order_test123"
        )
        event = _seed_event(fake_event_repo, capacity=10)

        with app.app_context(), pytest.raises(TaskEnqueueError):
            booking_service.create_booking(user_id=5, event_id=event.id, quantity=1)


class TestCreateBookingTransactionRollback:
    """Integration test against a real DB — fakes can't prove real rollback."""

    def test_capacity_reservation_rolls_back_on_downstream_failure(
        self, app, monkeypatch
    ):
        from app.extensions import db
        from app.events.repository import EventRepository
        from app.bookings.repository import BookingRepository
        from app.payments.repository import PaymentRepository

        monkeypatch.setattr(
            "app.bookings.service.create_order", lambda amount: "order_test123"
        )

        with app.app_context():
            event_repo = EventRepository()
            event = event_repo.create(
                user_id=1,
                name="Concert",
                date=datetime(2026, 1, 1, 18, 0),
                venue="Hall A",
                city="Bengaluru",
                capacity=10,
                tickets_sold=0,
                price=Decimal("10.00"),
            )

            service = BookingService(
                booking_repository=BookingRepository(),
                event_repository=event_repo,
                payment_repository=PaymentRepository(),
            )

            def _boom(*args, **kwargs):
                raise RuntimeError("simulated payment insert failure")

            original_create = PaymentRepository.create
            PaymentRepository.create = _boom
            try:
                with pytest.raises(RuntimeError):
                    service.create_booking(user_id=5, event_id=event.id, quantity=3)
            finally:
                PaymentRepository.create = original_create

            db.session.rollback()
            reloaded = event_repo.get_by_id(event.id)
            assert reloaded.tickets_sold == 0  # capacity reservation was rolled back
