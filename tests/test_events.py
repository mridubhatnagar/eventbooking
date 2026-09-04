from datetime import datetime
from decimal import Decimal

import pytest

from app.events.service import EventService
from app.events.tasks import notify_event_update
from app.enums import JobStatus, Role


@pytest.fixture
def event_service(fake_event_repo):
    return EventService(event_repository=fake_event_repo)


ORGANIZER_ID = 1
OTHER_ORGANIZER_ID = 2


def _create_event(event_service):
    return event_service.create_event(
        ORGANIZER_ID,
        "Concert",
        datetime(2026, 1, 1, 18, 0),
        "Hall A",
        "Bengaluru",
        capacity=100,
        price=Decimal("10.00"),
    )


class TestCreateEvent:
    def test_create_event_sets_tickets_sold_to_zero(self, event_service):
        event = _create_event(event_service)

        assert event.tickets_sold == 0
        assert event.capacity_remaining == 100
        assert event.user_id == ORGANIZER_ID


class TestListEvents:
    @pytest.mark.parametrize(
        "filter_city,expected_names",
        [
            (None, {"Concert", "Play"}),
            ("Bengaluru", {"Concert"}),
            ("Mumbai", {"Play"}),
            ("Delhi", set()),
        ],
    )
    def test_list_filters_by_city(self, event_service, filter_city, expected_names):
        _create_event(event_service)
        event_service.create_event(
            ORGANIZER_ID,
            "Play",
            datetime(2026, 1, 2, 18, 0),
            "Theatre B",
            "Mumbai",
            capacity=50,
            price=Decimal("5.00"),
        )

        events = event_service.list_events(city=filter_city)

        assert {e.name for e in events} == expected_names


class TestGetEvent:
    def test_get_nonexistent_event_raises(self, event_service):
        with pytest.raises(ValueError, match="not found"):
            event_service.get_event(999)


class TestUpdateEvent:
    def test_owner_can_update(self, app, event_service, monkeypatch):
        monkeypatch.setattr(notify_event_update, "delay", lambda *a, **kw: None)
        event = _create_event(event_service)

        with app.app_context():
            updated = event_service.update_event(event.id, ORGANIZER_ID, venue="Hall B")

        assert updated.venue == "Hall B"

    def test_non_owner_cannot_update(self, app, event_service, monkeypatch):
        monkeypatch.setattr(notify_event_update, "delay", lambda *a, **kw: None)
        event = _create_event(event_service)

        with app.app_context(), pytest.raises(PermissionError):
            event_service.update_event(event.id, OTHER_ORGANIZER_ID, venue="Hall B")

    def test_update_nonexistent_event_raises(self, app, event_service):
        with app.app_context(), pytest.raises(ValueError, match="not found"):
            event_service.update_event(999, ORGANIZER_ID, venue="Hall B")

    def test_update_triggers_notification_task(self, app, event_service, monkeypatch):
        calls = []
        monkeypatch.setattr(
            notify_event_update, "delay", lambda event_id: calls.append(event_id)
        )
        event = _create_event(event_service)

        with app.app_context():
            event_service.update_event(event.id, ORGANIZER_ID, venue="Hall B")

        assert calls == [event.id]


def _valid_event_payload(**overrides):
    payload = {
        "name": "Concert",
        "date": "2026-01-01T18:00:00",
        "venue": "Hall A",
        "city": "Bengaluru",
        "capacity": 100,
        "price": "10.00",
    }
    payload.update(overrides)
    return payload


class TestCreateEventEndpoint:
    """HTTP-layer: JWT enforcement, RBAC, request validation."""

    def test_missing_jwt_returns_401(self, client):
        response = client.post("/events", json=_valid_event_payload())

        assert response.status_code == 401

    def test_invalid_jwt_returns_422(self, client):
        response = client.post(
            "/events",
            json=_valid_event_payload(),
            headers={"Authorization": "Bearer not-a-real-token"},
        )

        assert response.status_code == 422

    def test_customer_role_forbidden(self, client, register_and_login):
        _, headers = register_and_login(Role.CUSTOMER)

        response = client.post("/events", json=_valid_event_payload(), headers=headers)

        assert response.status_code == 403

    def test_organizer_can_create_event(self, client, register_and_login):
        _, headers = register_and_login(Role.ORGANIZER)

        response = client.post("/events", json=_valid_event_payload(), headers=headers)

        assert response.status_code == 201
        assert response.get_json()["data"]["name"] == "Concert"

    def test_missing_required_field_returns_400(self, client, register_and_login):
        _, headers = register_and_login(Role.ORGANIZER)
        payload = _valid_event_payload()
        del payload["name"]

        response = client.post("/events", json=payload, headers=headers)

        assert response.status_code == 400

    def test_non_positive_capacity_returns_400(self, client, register_and_login):
        _, headers = register_and_login(Role.ORGANIZER)

        response = client.post(
            "/events", json=_valid_event_payload(capacity=0), headers=headers
        )

        assert response.status_code == 400


class TestGetEventEndpoint:
    def test_get_nonexistent_event_returns_404(self, client, register_and_login):
        _, headers = register_and_login(Role.CUSTOMER)

        response = client.get("/events/999999", headers=headers)

        assert response.status_code == 404

    def test_get_event_requires_jwt(self, client):
        response = client.get("/events/1")

        assert response.status_code == 401


class TestUpdateEventEndpoint:
    def test_customer_role_forbidden(self, client, register_and_login):
        _, organizer_headers = register_and_login(Role.ORGANIZER)
        created = client.post(
            "/events", json=_valid_event_payload(), headers=organizer_headers
        ).get_json()["data"]

        _, customer_headers = register_and_login(Role.CUSTOMER)
        response = client.patch(
            f"/events/{created['id']}",
            json={"venue": "Hall B"},
            headers=customer_headers,
        )

        assert response.status_code == 403

    def test_non_owner_organizer_returns_403(self, client, register_and_login):
        _, owner_headers = register_and_login(Role.ORGANIZER)
        created = client.post(
            "/events", json=_valid_event_payload(), headers=owner_headers
        ).get_json()["data"]

        _, other_headers = register_and_login(Role.ORGANIZER)
        response = client.patch(
            f"/events/{created['id']}",
            json={"venue": "Hall B"},
            headers=other_headers,
        )

        assert response.status_code == 403

    def test_owner_can_update_and_task_is_triggered(
        self, client, register_and_login, monkeypatch
    ):
        calls = []
        monkeypatch.setattr(
            notify_event_update, "delay", lambda event_id: calls.append(event_id)
        )
        _, headers = register_and_login(Role.ORGANIZER)
        created = client.post(
            "/events", json=_valid_event_payload(), headers=headers
        ).get_json()["data"]

        response = client.patch(
            f"/events/{created['id']}", json={"venue": "Hall B"}, headers=headers
        )

        assert response.status_code == 200
        assert response.get_json()["data"]["venue"] == "Hall B"
        assert calls == [created["id"]]


class TestNotifyEventUpdateTask:
    """Direct execution of the Celery task body (Background Task 2 in
    PLAN.md) — proves it notifies every booked customer, not just that it
    was enqueued."""

    def test_notifies_each_booked_customer_and_records_success_job(self, app, capsys):
        from app.users.repository import UserRepository
        from app.events.repository import EventRepository
        from app.bookings.repository import BookingRepository
        from app.jobs.repository import JobRepository

        with app.app_context():
            organizer = UserRepository().create(
                email="organizer@test.com",
                phone=None,
                password_hash="x",
                role=Role.ORGANIZER,
            )
            event = EventRepository().create(
                user_id=organizer.id,
                name="Concert",
                date=datetime(2026, 1, 1, 18, 0),
                venue="Hall A",
                city="Bengaluru",
                capacity=10,
                tickets_sold=0,
                price=Decimal("10.00"),
            )
            customer_a = UserRepository().create(
                email="a@test.com", phone=None, password_hash="x", role=Role.CUSTOMER
            )
            customer_b = UserRepository().create(
                email="b@test.com", phone=None, password_hash="x", role=Role.CUSTOMER
            )
            BookingRepository().create(
                user_id=customer_a.id, event_id=event.id, quantity=1
            )
            BookingRepository().create(
                user_id=customer_b.id, event_id=event.id, quantity=2
            )

            notify_event_update.apply(args=[event.id])

            captured = capsys.readouterr()
            assert customer_a.email in captured.out
            assert customer_b.email in captured.out

            jobs = JobRepository().list(event_id=event.id)
            assert len(jobs) == 1
            assert jobs[0].status == JobStatus.SUCCESS

    def test_no_bookings_still_records_success_job(self, app, capsys):
        from app.users.repository import UserRepository
        from app.events.repository import EventRepository
        from app.jobs.repository import JobRepository

        with app.app_context():
            organizer = UserRepository().create(
                email="organizer2@test.com",
                phone=None,
                password_hash="x",
                role=Role.ORGANIZER,
            )
            event = EventRepository().create(
                user_id=organizer.id,
                name="Empty",
                date=datetime(2026, 1, 1, 18, 0),
                venue="Hall A",
                city="Bengaluru",
                capacity=10,
                tickets_sold=0,
                price=Decimal("10.00"),
            )

            notify_event_update.apply(args=[event.id])

            jobs = JobRepository().list(event_id=event.id)
            assert len(jobs) == 1
            assert jobs[0].status == JobStatus.SUCCESS
