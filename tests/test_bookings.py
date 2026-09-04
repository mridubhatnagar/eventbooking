from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.bookings.service import BookingService
from app.bookings.tasks import send_booking_confirmation
from app.exceptions import GatewayError, TaskEnqueueError
from app.payments.tasks import request_payment
from app.enums import JobStatus, Role

FUTURE_DATE = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=365)


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
        date=FUTURE_DATE,
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

    def test_booking_past_event_raises(self, app, booking_service, fake_event_repo):
        past_event = fake_event_repo.create(
            user_id=1,
            name="Old Concert",
            date=FUTURE_DATE - timedelta(days=730),
            venue="Hall A",
            city="Bengaluru",
            capacity=10,
            tickets_sold=0,
            price=Decimal("10.00"),
        )

        with app.app_context(), pytest.raises(ValueError, match="past event"):
            booking_service.create_booking(
                user_id=5, event_id=past_event.id, quantity=1
            )

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
                date=FUTURE_DATE,
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


def _time_fields(dt):
    hour_12 = dt.hour % 12 or 12
    return {
        "event_date": dt.date().isoformat(),
        "hour": hour_12,
        "minute": dt.minute,
        "meridiem": "AM" if dt.hour < 12 else "PM",
    }


def _create_event_http(client, organizer_headers, capacity=10):
    response = client.post(
        "/events",
        json={
            "name": "Concert",
            "venue": "Hall A",
            "city": "Bengaluru",
            "capacity": capacity,
            "price": "10.00",
            **_time_fields(FUTURE_DATE),
        },
        headers=organizer_headers,
    )
    assert response.status_code == 201, response.get_json()
    return response.get_json()["data"]


class TestCreateBookingEndpoint:
    """HTTP-layer: JWT enforcement, RBAC, request validation."""

    def test_missing_jwt_returns_401(self, client):
        response = client.post("/bookings", json={"event_id": 1, "quantity": 1})

        assert response.status_code == 401

    def test_organizer_role_forbidden(self, client, register_and_login):
        _, headers = register_and_login(Role.ORGANIZER)

        response = client.post(
            "/bookings", json={"event_id": 1, "quantity": 1}, headers=headers
        )

        assert response.status_code == 403

    def test_non_positive_quantity_returns_400(self, client, register_and_login):
        _, headers = register_and_login(Role.CUSTOMER)

        response = client.post(
            "/bookings", json={"event_id": 1, "quantity": 0}, headers=headers
        )

        assert response.status_code == 400

    def test_past_event_returns_400(self, app, client, register_and_login):
        from app.events.repository import EventRepository

        organizer_id, _ = register_and_login(Role.ORGANIZER)
        with app.app_context():
            past_event = EventRepository().create(
                user_id=organizer_id,
                name="Old Concert",
                date=FUTURE_DATE - timedelta(days=730),
                venue="Hall A",
                city="Bengaluru",
                capacity=10,
                tickets_sold=0,
                price=Decimal("10.00"),
            )
            past_event_id = past_event.id

        _, customer_headers = register_and_login(Role.CUSTOMER)
        response = client.post(
            "/bookings",
            json={"event_id": past_event_id, "quantity": 1},
            headers=customer_headers,
        )

        assert response.status_code == 400


class TestBookingErrorMapping:
    """Proves app/__init__.py's error handlers actually translate service-layer
    exceptions into the documented HTTP status codes, end-to-end through the
    real Flask routing/JWT/validation stack."""

    def test_gateway_error_returns_502(
        self, client, register_and_login, monkeypatch, caplog
    ):
        organizer_id, organizer_headers = register_and_login(Role.ORGANIZER)
        event = _create_event_http(client, organizer_headers)

        monkeypatch.setattr(
            "app.bookings.service.create_order",
            lambda amount: (_ for _ in ()).throw(GatewayError("gateway unreachable")),
        )
        _, customer_headers = register_and_login(Role.CUSTOMER)

        with caplog.at_level("ERROR"):
            response = client.post(
                "/bookings",
                json={"event_id": event["id"], "quantity": 1},
                headers=customer_headers,
            )

        assert response.status_code == 502
        assert "gateway unreachable" in caplog.text

    def test_task_enqueue_failure_returns_503(
        self, client, register_and_login, monkeypatch, caplog
    ):
        _, organizer_headers = register_and_login(Role.ORGANIZER)
        event = _create_event_http(client, organizer_headers)

        monkeypatch.setattr(
            "app.bookings.service.create_order", lambda amount: "order_test123"
        )
        monkeypatch.setattr(
            request_payment,
            "delay",
            lambda *a, **kw: (_ for _ in ()).throw(ConnectionError("broker down")),
        )
        _, customer_headers = register_and_login(Role.CUSTOMER)

        with caplog.at_level("ERROR"):
            response = client.post(
                "/bookings",
                json={"event_id": event["id"], "quantity": 1},
                headers=customer_headers,
            )

        assert response.status_code == 503
        assert "broker down" in caplog.text


class TestGetBookingEndpoint:
    def _book(self, client, customer_headers, event_id, monkeypatch, quantity=1):
        monkeypatch.setattr(
            "app.bookings.service.create_order", lambda amount: "order_test123"
        )
        monkeypatch.setattr(request_payment, "delay", lambda *a, **kw: None)
        response = client.post(
            "/bookings",
            json={"event_id": event_id, "quantity": quantity},
            headers=customer_headers,
        )
        assert response.status_code == 201, response.get_json()
        return response.get_json()["data"]

    def test_owner_can_fetch_own_booking(self, client, register_and_login, monkeypatch):
        _, organizer_headers = register_and_login(Role.ORGANIZER)
        event = _create_event_http(client, organizer_headers)
        _, customer_headers = register_and_login(Role.CUSTOMER)
        booking = self._book(client, customer_headers, event["id"], monkeypatch)

        response = client.get(f"/bookings/{booking['id']}", headers=customer_headers)

        assert response.status_code == 200
        assert response.get_json()["data"]["id"] == booking["id"]

    def test_non_owner_gets_404(self, client, register_and_login, monkeypatch):
        _, organizer_headers = register_and_login(Role.ORGANIZER)
        event = _create_event_http(client, organizer_headers)
        _, owner_headers = register_and_login(Role.CUSTOMER)
        booking = self._book(client, owner_headers, event["id"], monkeypatch)

        _, other_headers = register_and_login(Role.CUSTOMER)
        response = client.get(f"/bookings/{booking['id']}", headers=other_headers)

        assert response.status_code == 404

    def test_nonexistent_booking_returns_404(self, client, register_and_login):
        _, headers = register_and_login(Role.CUSTOMER)

        response = client.get("/bookings/999999", headers=headers)

        assert response.status_code == 404


class TestListBookingsEndpoint:
    def test_list_is_scoped_to_requesting_user(
        self, client, register_and_login, monkeypatch
    ):
        order_ids = iter(["order_test123", "order_test456"])
        monkeypatch.setattr(
            "app.bookings.service.create_order", lambda amount: next(order_ids)
        )
        monkeypatch.setattr(request_payment, "delay", lambda *a, **kw: None)

        _, organizer_headers = register_and_login(Role.ORGANIZER)
        event = _create_event_http(client, organizer_headers)

        _, mine_headers = register_and_login(Role.CUSTOMER)
        client.post(
            "/bookings",
            json={"event_id": event["id"], "quantity": 1},
            headers=mine_headers,
        )

        _, other_headers = register_and_login(Role.CUSTOMER)
        client.post(
            "/bookings",
            json={"event_id": event["id"], "quantity": 2},
            headers=other_headers,
        )

        response = client.get("/bookings", headers=mine_headers)

        assert response.status_code == 200
        bookings = response.get_json()["data"]
        assert len(bookings) == 1
        assert bookings[0]["quantity"] == 1


class TestSendBookingConfirmationTask:
    """Direct execution of the Celery task body (Background Task 1 in
    PLAN.md) — proves its actual side effects, not just that it was enqueued."""

    def test_logs_confirmation_and_records_success_job(self, app, caplog):
        from app.users.repository import UserRepository
        from app.events.repository import EventRepository
        from app.bookings.repository import BookingRepository
        from app.jobs.repository import JobRepository
        from app.enums import Role as _Role

        with app.app_context():
            user = UserRepository().create(
                email="confirm-me@test.com",
                phone=None,
                password_hash="x",
                role=_Role.CUSTOMER,
            )
            event = EventRepository().create(
                user_id=1,
                name="Concert",
                date=FUTURE_DATE,
                venue="Hall A",
                city="Bengaluru",
                capacity=10,
                tickets_sold=0,
                price=Decimal("10.00"),
            )
            booking = BookingRepository().create(
                user_id=user.id, event_id=event.id, quantity=1
            )

            with caplog.at_level("INFO"):
                send_booking_confirmation.apply(
                    args=[booking.id], kwargs={"payment_id": 42}
                )

            assert user.email in caplog.text
            assert str(booking.id) in caplog.text

            jobs = JobRepository().list(payment_id=42)
            assert len(jobs) == 1
            assert jobs[0].status == JobStatus.SUCCESS
