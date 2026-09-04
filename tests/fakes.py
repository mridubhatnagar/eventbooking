"""In-memory fake repositories for unit-testing services in isolation,
without touching a real database. Each fake implements the same interface
the real Repository classes do (see each domain's dao_interface.py)."""

from datetime import datetime, timezone

from app.users.model import User
from app.events.model import Event
from app.bookings.model import Booking
from app.payments.model import Payment
from app.organizer_profiles.model import OrganizerProfile
from app.reviews.model import Review


class _FakeRepositoryBase:
    model_cls = None

    def __init__(self):
        self._store = {}
        self._next_id = 1

    def _new_id(self):
        id_ = self._next_id
        self._next_id += 1
        return id_

    def get_by_id(self, id_):
        return self._store.get(id_)

    def create(self, commit=True, **kwargs):
        obj = self.model_cls(**kwargs)
        obj.id = self._new_id()
        now = datetime.now(timezone.utc)
        obj.created_at = now
        obj.updated_at = now
        self._store[obj.id] = obj
        return obj

    def update(self, id, **kwargs):
        obj = self._store.get(id)
        if not obj:
            return None
        for key, value in kwargs.items():
            setattr(obj, key, value)
        obj.updated_at = datetime.now(timezone.utc)
        return obj

    def list(self, **filters):
        return [
            obj
            for obj in self._store.values()
            if all(getattr(obj, k) == v for k, v in filters.items())
        ]


class FakeUserRepository(_FakeRepositoryBase):
    model_cls = User

    def get_by_email(self, email):
        return next((u for u in self._store.values() if u.email == email), None)


class FakeEventRepository(_FakeRepositoryBase):
    model_cls = Event

    def try_reserve_capacity(self, event_id, quantity, commit=True):
        event = self._store.get(event_id)
        if not event:
            return False
        if event.tickets_sold + quantity > event.capacity:
            return False
        event.tickets_sold += quantity
        return True


class FakeBookingRepository(_FakeRepositoryBase):
    model_cls = Booking


class FakePaymentRepository(_FakeRepositoryBase):
    model_cls = Payment

    def get_by_order_id(self, order_id):
        return next((p for p in self._store.values() if p.order_id == order_id), None)

    def get_by_booking_id(self, booking_id):
        return next(
            (p for p in self._store.values() if p.booking_id == booking_id), None
        )


class FakeOrganizerProfileRepository(_FakeRepositoryBase):
    model_cls = OrganizerProfile

    def get_by_user_id(self, user_id):
        return next((p for p in self._store.values() if p.user_id == user_id), None)


class FakeReviewRepository(_FakeRepositoryBase):
    model_cls = Review

    def get_by_booking_id(self, booking_id):
        return next(
            (r for r in self._store.values() if r.booking_id == booking_id), None
        )
