from flask import Blueprint, jsonify, request

from app.users.service import AuthService
from app.users.schemas import RegisterRequest, LoginRequest
from app.docs import api

bp = Blueprint("auth", __name__, url_prefix="/auth")
auth_service = AuthService()


@bp.post("/register")
@api.validate(json=RegisterRequest, tags=["auth"])
def register():
    data = request.context.json

    try:
        user = auth_service.register(data.email, data.phone, data.password, data.role)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({"id": user.id, "email": user.email, "role": user.role}), 201


@bp.post("/login")
@api.validate(json=LoginRequest, tags=["auth"])
def login():
    data = request.context.json

    try:
        token = auth_service.login(data.email, data.password)
    except ValueError as e:
        return jsonify({"error": str(e)}), 401

    return jsonify({"access_token": token}), 200
