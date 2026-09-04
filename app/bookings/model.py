from app.extensions import db
from app.base import TimestampMixin
from app.enums import BookingStatus, PaymentStatus


class Booking(db.Model, TimestampMixin):
    __tablename__ = "bookings"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    event_id = db.Column(
        db.Integer, db.ForeignKey("events.id"), nullable=False, index=True
    )
    quantity = db.Column(db.Integer, nullable=False)

    # Cross-domain relationship resolved by class name string (no import needed,
    # avoids coupling the bookings domain to the payments module directly).
    payment = db.relationship("Payment", backref="booking", uselist=False, lazy=True)

    @property
    def status(self):
        """Derived from Payment.status — no separate status stored (single source of truth)."""
        if not self.payment:
            return BookingStatus.PENDING
        if self.payment.status == PaymentStatus.PROCESSED:
            return BookingStatus.CONFIRMED
        if self.payment.status == PaymentStatus.FAILED:
            return BookingStatus.FAILED
        return BookingStatus.PENDING
