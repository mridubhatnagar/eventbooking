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


class Meridiem(StrEnum):
    AM = "AM"
    PM = "PM"


class Industry(StrEnum):
    MUSIC = "MUSIC"
    SPORTS = "SPORTS"
    CORPORATE = "CORPORATE"
    COMEDY = "COMEDY"
    THEATRE_ARTS = "THEATRE_ARTS"
    CONFERENCES_SEMINARS = "CONFERENCES_SEMINARS"
    EDUCATION = "EDUCATION"
    FOOD_BEVERAGE = "FOOD_BEVERAGE"
    TECHNOLOGY = "TECHNOLOGY"
    FASHION = "FASHION"
    FILM_ENTERTAINMENT = "FILM_ENTERTAINMENT"
    COMMUNITY_NONPROFIT = "COMMUNITY_NONPROFIT"
    OTHER = "OTHER"
