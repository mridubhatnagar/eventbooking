from enum import StrEnum


class Role(StrEnum):
    CUSTOMER = "customer"
    ORGANIZER = "organizer"


class PaymentStatus(StrEnum):
    PENDING = "PENDING"
    REQUESTED = "REQUESTED"
    PROCESSED = "PROCESSED"
    FAILED = "FAILED"


class GatewayStatus(StrEnum):
    CREATED = "created"
    CAPTURED = "captured"
    FAILED = "failed"


class BookingStatus(StrEnum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    FAILED = "FAILED"


class JobStatus(StrEnum):
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class WebhookEvent(StrEnum):
    PAYMENT_CAPTURED = "payment.captured"
    PAYMENT_FAILED = "payment.failed"
