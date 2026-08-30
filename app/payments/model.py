from app.extensions import db
from app.base import TimestampMixin
from app.enums import GatewayStatus, PaymentStatus


class Payment(db.Model, TimestampMixin):
    __tablename__ = "payments"

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(
        db.Integer, db.ForeignKey("bookings.id"), nullable=False, unique=True
    )
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    order_id = db.Column(db.String(64), unique=True, nullable=True, index=True)

    # Mirrors Razorpay's own lifecycle: created -> captured
    gateway_status = db.Column(
        db.String(20), nullable=False, default=GatewayStatus.CREATED
    )

    # Internal status: PENDING -> REQUESTED -> PROCESSED | FAILED
    status = db.Column(db.String(20), nullable=False, default=PaymentStatus.PENDING)
