from app.events.repository import EventRepository
from app.events.tasks import notify_event_update
from app.exceptions import TaskEnqueueError


class EventService:
    def __init__(self, event_repository=None):
        self.event_repository = event_repository or EventRepository()

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

    def list_events(self, city=None):
        filters = {"city": city} if city else {}
        return self.event_repository.list(**filters)

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
