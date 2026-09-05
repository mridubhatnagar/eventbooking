from app.extensions import db
from app.bookings.model import Booking
from app.bookings.dao_interface import IDAO


class BookingRepository(IDAO):
    def get_by_id(self, booking_id):
        return db.session.get(Booking, booking_id)

    def create(self, commit=True, **kwargs):
        booking = Booking(**kwargs)
        db.session.add(booking)
        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return booking

    def update(self, id, **kwargs):
        booking = self.get_by_id(id)
        if not booking:
            return None
        for key, value in kwargs.items():
            setattr(booking, key, value)
        db.session.commit()
        return booking

    def list(self, **filters):
        return Booking.query.filter_by(**filters).all()

    def list_paginated(self, limit, offset, **filters):
        query = Booking.query.filter_by(**filters)
        total = query.count()
        items = query.offset(offset).limit(limit).all()
        return items, total
