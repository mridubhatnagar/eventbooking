from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.decorators import role_required
from app.events.service import EventService
from app.events.schemas import CreateEventRequest, UpdateEventRequest, ListEventsQuery
from app.enums import Role
from app.docs import api

bp = Blueprint("events", __name__, url_prefix="/events")
event_service = EventService()


def _serialize(event):
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
    }


@bp.post("")
@role_required(Role.ORGANIZER)
@api.validate(json=CreateEventRequest, tags=["events"])
def create_event():
    data = request.context.json

    user_id = int(get_jwt_identity())
    event = event_service.create_event(
        user_id, data.name, data.date, data.venue, data.city, data.capacity, data.price
    )
    return jsonify(_serialize(event)), 201


@bp.get("")
@jwt_required()
@api.validate(query=ListEventsQuery, tags=["events"])
def list_events():
    city = request.context.query.city
    events = event_service.list_events(city=city)
    return jsonify([_serialize(e) for e in events]), 200


@bp.get("/<int:event_id>")
@jwt_required()
@api.validate(tags=["events"])
def get_event(event_id):
    try:
        event = event_service.get_event(event_id)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    return jsonify(_serialize(event)), 200


@bp.patch("/<int:event_id>")
@role_required(Role.ORGANIZER)
@api.validate(json=UpdateEventRequest, tags=["events"])
def update_event(event_id):
    data = request.context.json

    fields = data.model_dump(exclude_none=True)
    user_id = int(get_jwt_identity())

    try:
        event = event_service.update_event(event_id, user_id, **fields)
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except PermissionError as e:
        return jsonify({"error": str(e)}), 403

    return jsonify(_serialize(event)), 200
