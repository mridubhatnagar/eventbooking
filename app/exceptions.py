class TaskEnqueueError(Exception):
    """Raised when a Celery task fails to enqueue (e.g. broker unreachable).
    Deliberately loud — a booking/event/payment write that already committed
    to the DB should not silently lose its follow-up background task."""


class GatewayError(Exception):
    """Raised when a call to the (mocked) payment gateway fails — e.g. order
    creation unreachable. Deliberately loud, same reasoning as TaskEnqueueError."""
