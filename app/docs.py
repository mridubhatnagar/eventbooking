import json

from spectree import SecurityScheme, SpecTree

JWT_SECURITY_NAME = "bearer_jwt"


def _envelope_validation_error(req, resp, req_validation_error, instance):
    """Rewrites spectree's own validation-error body into the
    {meta, data, error} envelope every other response uses."""
    if req_validation_error is None or resp is None:
        return
    try:
        errors = req_validation_error.errors(include_context=False)
    except TypeError:
        errors = req_validation_error.errors()
    resp.set_data(
        json.dumps(
            {
                "meta": {},
                "data": None,
                "error": {"message": "validation error", "details": errors},
            }
        )
    )


api = SpecTree(
    "flask",
    title="Event Booking System API",
    version="1.0.0",
    validation_error_status=400,
    mode="strict",
    before=_envelope_validation_error,
    security_schemes=[
        SecurityScheme(
            name=JWT_SECURITY_NAME,
            data={"type": "http", "scheme": "bearer", "bearerFormat": "JWT"},
        ),
    ],
)

JWT_SECURITY = {JWT_SECURITY_NAME: []}
