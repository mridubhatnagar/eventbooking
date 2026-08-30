from datetime import datetime
from decimal import Decimal

import pytest

from app.events.service import EventService
from app.events.tasks import notify_event_update


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
