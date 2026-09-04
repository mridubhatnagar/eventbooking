from app.extensions import db
from app.bookings.repository import BookingRepository
from app.events.repository import EventRepository
from app.payments.repository import PaymentRepository
from app.payments.gateway_client import create_order
from app.payments.tasks import request_payment
from app.enums import GatewayStatus, PaymentStatus
from app.exceptions import TaskEnqueueError
from app.timezone import now_ist


class BookingService:
    def __init__(
        self,
        booking_repository=None,
        event_repository=None,
        payment_repository=None,
    ):
        self.booking_repository = booking_repository or BookingRepository()
        self.event_repository = event_repository or EventRepository()
        self.payment_repository = payment_repository or PaymentRepository()

    def create_booking(self, user_id, event_id, quantity):
        event = self.event_repository.get_by_id(event_id)
        if not event:
            raise ValueError("event not found")

        if event.date <= now_ist():
            raise ValueError("cannot book a past event")

        if quantity < 1:
            raise ValueError("quantity must be at least 1")

        # Booking Rule (frozen in PLAN.md): check capacity before booking, and
        # update Event's sold count after. Done as one atomic conditional
        # UPDATE (no explicit locking) so concurrent bookings can't oversell.
        #
        # All three writes (capacity reservation, Booking, Payment) share one
        # transaction — commit=False + a single commit at the end means a
        # failure partway through rolls everything back, including the
        # capacity reservation. This also covers create_order()'s gateway
        # call: if it raises GatewayError, nothing here gets committed.
        try:
            if not self.event_repository.try_reserve_capacity(
                event_id, quantity, commit=False
            ):
                raise ValueError("not enough capacity remaining for this event")

            booking = self.booking_repository.create(
                commit=False, user_id=user_id, event_id=event_id, quantity=quantity
            )

            amount = event.price * quantity
            order_id = create_order(amount)

            payment = self.payment_repository.create(
                commit=False,
                booking_id=booking.id,
                amount=amount,
                order_id=order_id,
                gateway_status=GatewayStatus.CREATED,
                status=PaymentStatus.PENDING,
            )

            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        # Deliberately loud: the booking/payment rows are already committed,
        # but if the broker is unreachable the payment flow can never start —
        # that's a real failure the caller must know about, not a silent one.
        try:
            request_payment.delay(payment.id)
        except Exception as e:
            raise TaskEnqueueError(
                f"booking {booking.id} was created but the payment flow "
                f"could not be started: {e}"
            ) from e

        return booking, payment

    def list_bookings(self, user_id):
        return self.booking_repository.list(user_id=user_id)

    def get_booking(self, booking_id, user_id):
        booking = self.booking_repository.get_by_id(booking_id)
        if not booking or booking.user_id != user_id:
            raise ValueError("booking not found")
        return booking
