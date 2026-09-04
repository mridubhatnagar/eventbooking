from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.decorators import role_required
from app.reviews.service import ReviewService
from app.reviews.schemas import CreateReviewRequest
from app.events.service import EventService
from app.enums import Role
from app.docs import api, JWT_SECURITY
from app.responses import success, error

bp = Blueprint("reviews", __name__)
review_service = ReviewService()
event_service = EventService()


def _serialize(review):
    return {
        "id": review.id,
        "booking_id": review.booking_id,
        "rating": review.rating,
        "review_text": review.review_text,
        "created_at": review.created_at.isoformat(),
    }


@bp.post("/bookings/<int:booking_id>/reviews")
@role_required(Role.CUSTOMER)
@api.validate(json=CreateReviewRequest, tags=["reviews"], security=JWT_SECURITY)
def create_review(booking_id):
    data = request.context.json
    user_id = int(get_jwt_identity())

    try:
        review = review_service.create_review(
            booking_id, user_id, data.rating, data.review_text
        )
    except LookupError as e:
        return error(str(e), 404)
    except ValueError as e:
        return error(str(e), 400)

    return success(_serialize(review), 201)


@bp.get("/events/<int:event_id>/reviews")
@jwt_required()
@api.validate(tags=["reviews"], security=JWT_SECURITY)
def list_event_reviews(event_id):
    try:
        event_service.get_event(event_id)
    except ValueError as e:
        return error(str(e), 404)

    reviews = review_service.list_for_event(event_id)
    return success([_serialize(r) for r in reviews], 200)
