from flask import Blueprint, request
from flask_jwt_extended import get_jwt_identity

from app.decorators import role_required
from app.bookings.service import BookingService
from app.bookings.schemas import CreateBookingRequest
from app.enums import Role
from app.docs import api, JWT_SECURITY
from app.responses import success, error

bp = Blueprint("bookings", __name__, url_prefix="/bookings")
booking_service = BookingService()


def _serialize(booking):
    return {
        "id": booking.id,
        "user_id": booking.user_id,
        "event_id": booking.event_id,
        "quantity": booking.quantity,
        "status": booking.status,
        "created_at": booking.created_at.isoformat(),
    }


@bp.post("")
@role_required(Role.CUSTOMER)
@api.validate(json=CreateBookingRequest, tags=["bookings"], security=JWT_SECURITY)
def create_booking():
    data = request.context.json

    user_id = int(get_jwt_identity())

    try:
        booking, _payment = booking_service.create_booking(
            user_id, data.event_id, data.quantity
        )
    except ValueError as e:
        return error(str(e), 400)

    return success(_serialize(booking), 201)


@bp.get("")
@role_required(Role.CUSTOMER)
@api.validate(tags=["bookings"], security=JWT_SECURITY)
def list_bookings():
    user_id = int(get_jwt_identity())
    bookings = booking_service.list_bookings(user_id)
    return success([_serialize(b) for b in bookings], 200)


@bp.get("/<int:booking_id>")
@role_required(Role.CUSTOMER)
@api.validate(tags=["bookings"], security=JWT_SECURITY)
def get_booking(booking_id):
    user_id = int(get_jwt_identity())
    try:
        booking = booking_service.get_booking(booking_id, user_id)
    except ValueError as e:
        return error(str(e), 404)
    return success(_serialize(booking), 200)
