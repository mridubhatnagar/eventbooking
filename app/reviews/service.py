from datetime import datetime, timezone

from app.reviews.repository import ReviewRepository
from app.bookings.repository import BookingRepository
from app.payments.repository import PaymentRepository
from app.events.repository import EventRepository
from app.enums import PaymentStatus


class ReviewService:
    def __init__(
        self,
        review_repository=None,
        booking_repository=None,
        payment_repository=None,
        event_repository=None,
    ):
        self.review_repository = review_repository or ReviewRepository()
        self.booking_repository = booking_repository or BookingRepository()
        self.payment_repository = payment_repository or PaymentRepository()
        self.event_repository = event_repository or EventRepository()

    def create_review(self, booking_id, user_id, rating, review_text=None):
        booking = self.booking_repository.get_by_id(booking_id)
        if not booking or booking.user_id != user_id:
            raise LookupError("booking not found")

        payment = self.payment_repository.get_by_booking_id(booking_id)
        if not payment or payment.status != PaymentStatus.PROCESSED:
            raise ValueError("booking must be confirmed before it can be reviewed")

        event = self.event_repository.get_by_id(booking.event_id)
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if event.date > now:
            raise ValueError("event has not taken place yet")

        if self.review_repository.get_by_booking_id(booking_id):
            raise ValueError("booking already reviewed")

        return self.review_repository.create(
            booking_id=booking_id, rating=rating, review_text=review_text
        )

    def list_for_event(self, event_id):
        bookings = self.booking_repository.list(event_id=event_id)
        reviews = (
            self.review_repository.get_by_booking_id(booking.id) for booking in bookings
        )
        return [review for review in reviews if review]
