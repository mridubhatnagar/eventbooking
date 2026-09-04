from flask import Blueprint, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.decorators import role_required
from app.events.service import EventService, EventHasBookingsError
from app.events.schemas import CreateEventRequest, UpdateEventRequest, ListEventsQuery
from app.organizer_profiles.service import OrganizerProfileService
from app.enums import Role
from app.docs import api, JWT_SECURITY
from app.responses import success, error

bp = Blueprint("events", __name__, url_prefix="/events")
event_service = EventService()
organizer_profile_service = OrganizerProfileService()


def _serialize_organizer(profile):
    return {
        "company_name": profile.company_name,
        "city": profile.city,
        "industry": profile.industry,
    }


def _serialize(event):
    organizer_profile = organizer_profile_service.get_by_user_id(event.user_id)
    return {
        "id": event.id,
        "user_id": event.user_id,
        "name": event.name,
        "date": event.date.isoformat(),
        "venue": event.venue,
        "city": event.city,
        "capacity": event.capacity,
        "tickets_sold": event.tickets_sold,
        "capacity_remaining": event.capacity_remaining,
        "price": str(event.price),
        "organizer": (
            _serialize_organizer(organizer_profile) if organizer_profile else None
        ),
    }


@bp.post("")
@role_required(Role.ORGANIZER)
@api.validate(json=CreateEventRequest, tags=["events"], security=JWT_SECURITY)
def create_event():
    data = request.context.json

    user_id = int(get_jwt_identity())
    event = event_service.create_event(
        user_id, data.name, data.date, data.venue, data.city, data.capacity, data.price
    )
    return success(_serialize(event), 201)


@bp.get("")
@jwt_required()
@api.validate(query=ListEventsQuery, tags=["events"], security=JWT_SECURITY)
def list_events():
    query = request.context.query
    events = event_service.list_events(
        city=query.city,
        date_from=query.date_from,
        date_to=query.date_to,
        industry=query.industry,
    )
    return success([_serialize(e) for e in events], 200)


@bp.get("/<int:event_id>")
@jwt_required()
@api.validate(tags=["events"], security=JWT_SECURITY)
def get_event(event_id):
    try:
        event = event_service.get_event(event_id)
    except ValueError as e:
        return error(str(e), 404)
    return success(_serialize(event), 200)


@bp.patch("/<int:event_id>")
@role_required(Role.ORGANIZER)
@api.validate(json=UpdateEventRequest, tags=["events"], security=JWT_SECURITY)
def update_event(event_id):
    data = request.context.json

    fields = data.model_dump(exclude_none=True)
    user_id = int(get_jwt_identity())

    try:
        event = event_service.update_event(event_id, user_id, **fields)
    except ValueError as e:
        return error(str(e), 404)
    except PermissionError as e:
        return error(str(e), 403)

    return success(_serialize(event), 200)


@bp.delete("/<int:event_id>")
@role_required(Role.ORGANIZER)
@api.validate(tags=["events"], security=JWT_SECURITY)
def delete_event(event_id):
    user_id = int(get_jwt_identity())

    try:
        event_service.delete_event(event_id, user_id)
    except ValueError as e:
        return error(str(e), 404)
    except PermissionError as e:
        return error(str(e), 403)
    except EventHasBookingsError as e:
        return error(str(e), 409)

    return success(None, 200)
