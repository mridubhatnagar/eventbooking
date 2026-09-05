from app.extensions import db
from app.events.model import Event
from app.events.dao_interface import IDAO


class EventRepository(IDAO):
    def get_by_id(self, event_id):
        return db.session.get(Event, event_id)

    def create(self, **kwargs):
        event = Event(**kwargs)
        db.session.add(event)
        db.session.commit()
        return event

    def update(self, id, **kwargs):
        event = self.get_by_id(id)
        if not event:
            return None
        for key, value in kwargs.items():
            setattr(event, key, value)
        db.session.commit()
        return event

    def list(self, **filters):
        return Event.query.filter_by(**filters).all()

    def list_filtered(
        self, city=None, date_from=None, date_to=None, user_ids=None, limit=20, offset=0
    ):
        query = Event.query
        if city:
            query = query.filter(Event.city == city)
        if date_from:
            query = query.filter(Event.date >= date_from)
        if date_to:
            query = query.filter(Event.date <= date_to)
        if user_ids is not None:
            query = query.filter(Event.user_id.in_(user_ids))
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return items, total

    def delete_if_no_bookings(self, id):
        """Atomically deletes only if tickets_sold == 0 — collapses the
        check-and-delete into one statement so a booking created between
        checking and deleting can't be missed (TOCTOU), mirroring
        try_reserve_capacity's atomic conditional UPDATE below.

        Returns True if deleted, False if the row now has bookings (or is
        already gone).
        """
        result = db.session.execute(
            db.delete(Event).where(Event.id == id, Event.tickets_sold == 0)
        )
        db.session.commit()
        return result.rowcount > 0

    def try_reserve_capacity(self, event_id, quantity, commit=True):
        """Atomically increments tickets_sold if capacity allows.

        Single conditional UPDATE — no explicit locking needed, Postgres'
        own atomicity prevents overselling under concurrent requests.
        Returns True if reserved, False if not enough capacity remained.

        commit=False lets a caller fold this into a larger transaction
        (flushes so the change is visible within that transaction either way).
        """
        result = db.session.execute(
            db.update(Event)
            .where(
                Event.id == event_id,
                Event.tickets_sold + quantity <= Event.capacity,
            )
            .values(tickets_sold=Event.tickets_sold + quantity)
        )
        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return result.rowcount > 0
