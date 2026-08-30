from functools import wraps

from flask import current_app, request
from flask_jwt_extended import jwt_required, get_jwt


def role_required(*roles):
    """RBAC guard — requires a valid JWT and a matching `role` claim."""

    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            if get_jwt().get("role") not in roles:
                return {"error": "forbidden"}, 403
            return fn(*args, **kwargs)

        return wrapper

    return decorator


def api_key_required(fn):
    """Guard for system-facing endpoints (not JWT) — e.g. the mock trigger."""

    @wraps(fn)
    def wrapper(*args, **kwargs):
        provided = request.headers.get("x-api-key")
        if not provided or provided != current_app.config["MOCK_TRIGGER_API_KEY"]:
            return {"error": "forbidden"}, 403
        return fn(*args, **kwargs)

    return wrapper
