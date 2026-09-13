from flask import Blueprint, request

from app.users.service import AuthService
from app.users.schemas import RegisterRequest, LoginRequest
from app.docs import api
from app.extensions import limiter
from app.responses import success, error

bp = Blueprint("auth", __name__, url_prefix="/v1")
auth_service = AuthService()


@bp.post("/users")
@limiter.limit("10 per hour")
@api.validate(json=RegisterRequest, tags=["auth"])
def register():
    data = request.context.json

    organizer_profile = (
        data.organizer_profile.model_dump() if data.organizer_profile else None
    )

    try:
        user = auth_service.register(
            data.email, data.phone, data.password, data.role, organizer_profile
        )
    except ValueError as e:
        return error(str(e), 400)

    return success({"id": user.id, "email": user.email, "role": user.role}, 201)


@bp.post("/sessions")
@limiter.limit("5 per minute")
@api.validate(json=LoginRequest, tags=["auth"])
def login():
    data = request.context.json

    try:
        token = auth_service.login(data.email, data.password)
    except ValueError as e:
        return error(str(e), 401)

    return success({"access_token": token}, 200)
