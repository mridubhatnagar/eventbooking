from app.extensions import db
from app.base import TimestampMixin


class Review(db.Model, TimestampMixin):
    __tablename__ = "reviews"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer, db.ForeignKey("bookings.id"), nullable=False, unique=True
    )
    rating = db.Column(db.Integer, nullable=False)
    review_text = db.Column(db.Text, nullable=True)

    # Cross-domain relationship resolved by class name string (no import needed,
    # avoids coupling the reviews domain to the bookings module directly).
    booking = db.relationship(
        "Booking", backref=db.backref("review", uselist=False), lazy=True
    )
