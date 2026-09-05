from datetime import datetime, time

from app.events.repository import EventRepository
from app.events.tasks import notify_event_update
from app.organizer_profiles.repository import OrganizerProfileRepository
from app.exceptions import TaskEnqueueError


class EventHasBookingsError(Exception):
    """Raised when deleting an event that already has bookings against it."""


class EventService:
    def __init__(self, event_repository=None, organizer_profile_repository=None):
        self.event_repository = event_repository or EventRepository()
        self.organizer_profile_repository = (
            organizer_profile_repository or OrganizerProfileRepository()
        )

    def create_event(self, user_id, name, date, venue, city, capacity, price):
        return self.event_repository.create(
            user_id=user_id,
            name=name,
            date=date,
            venue=venue,
            city=city,
            capacity=capacity,
            tickets_sold=0,
            price=price,
        )

    def list_events(
        self, city=None, date_from=None, date_to=None, industry=None, limit=20, offset=0
    ):
        user_ids = None
        if industry:
            profiles = self.organizer_profile_repository.list(industry=industry)
            user_ids = [p.user_id for p in profiles]

        # date_from/date_to are plain calendar dates (customers pick a date,
        # not a datetime) — widen to the full day so date_to's day is
        # inclusive rather than cutting off at its midnight.
        date_from_dt = datetime.combine(date_from, time.min) if date_from else None
        date_to_dt = datetime.combine(date_to, time.max) if date_to else None

        return self.event_repository.list_filtered(
            city=city,
            date_from=date_from_dt,
            date_to=date_to_dt,
            user_ids=user_ids,
            limit=limit,
            offset=offset,
        )

    def get_event(self, event_id):
        event = self.event_repository.get_by_id(event_id)
        if not event:
            raise ValueError("event not found")
        return event

    def update_event(self, event_id, requester_id, **fields):
        event = self.get_event(event_id)
        if event.user_id != requester_id:
            raise PermissionError("not the organizer of this event")

        updated_event = self.event_repository.update(event_id, **fields)

        try:
            notify_event_update.delay(event_id)
        except Exception as e:
            raise TaskEnqueueError(
                f"event {event_id} was updated but the notification task "
                f"could not be started: {e}"
            ) from e

        return updated_event

    def delete_event(self, event_id, requester_id):
        event = self.get_event(event_id)
        if event.user_id != requester_id:
            raise PermissionError("not the organizer of this event")

        # Atomic conditional delete (not a separate tickets_sold check then a
        # delete) — see EventRepository.delete_if_no_bookings for why.
        if not self.event_repository.delete_if_no_bookings(event_id):
            raise EventHasBookingsError("cannot delete an event with existing bookings")
