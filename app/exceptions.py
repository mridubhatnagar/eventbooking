class TaskEnqueueError(Exception):
    """Raised when a Celery task fails to enqueue (e.g. broker unreachable).
    Deliberately loud — a booking/event/payment write that already committed
    to the DB should not silently lose its follow-up background task."""
