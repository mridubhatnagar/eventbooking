from app.payments.repository import PaymentRepository
from app.bookings.tasks import send_booking_confirmation
from app.enums import GatewayStatus, PaymentStatus, WebhookEvent
from app.exceptions import TaskEnqueueError

EVENT_TO_STATUS = {
    WebhookEvent.PAYMENT_CAPTURED: (PaymentStatus.PROCESSED, GatewayStatus.CAPTURED),
    WebhookEvent.PAYMENT_FAILED: (PaymentStatus.FAILED, GatewayStatus.FAILED),
}


class PaymentService:
    def __init__(self, payment_repository=None):
        self.payment_repository = payment_repository or PaymentRepository()

    def process_webhook_event(self, order_id, event_type):
        payment = self.payment_repository.get_by_order_id(order_id)
        if not payment:
            raise ValueError("payment not found for this order_id")

        if event_type not in EVENT_TO_STATUS:
            raise ValueError(f"unknown event type: {event_type}")

        status, gateway_status = EVENT_TO_STATUS[event_type]
        payment = self.payment_repository.update(
            payment.id, status=status, gateway_status=gateway_status
        )

        # Payment Flow step 5 (frozen in PLAN.md): only on PROCESSED, enqueue
        # the Booking Confirmation task. FAILED leaves the booking unconfirmed.
        if status == PaymentStatus.PROCESSED:
            try:
                send_booking_confirmation.delay(
                    payment.booking_id, payment_id=payment.id
                )
            except Exception as e:
                raise TaskEnqueueError(
                    f"payment {payment.id} was marked PROCESSED but the "
                    f"booking confirmation task could not be started: {e}"
                ) from e

        return payment
