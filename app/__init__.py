from flask import Flask
from werkzeug.exceptions import HTTPException

from app.config import Config
from app.extensions import db, jwt, migrate, configure_celery
from app.exceptions import TaskEnqueueError, GatewayError
from app.docs import api
from app.responses import error

# Import every domain's model so SQLAlchemy's metadata knows about all
# tables — Alembic's autogenerate needs every model imported before it
# diffs the metadata against the DB.
from app.users.model import User  # noqa: F401
from app.events.model import Event  # noqa: F401
from app.bookings.model import Booking  # noqa: F401
from app.payments.model import Payment  # noqa: F401
from app.jobs.model import Job  # noqa: F401
from app.organizer_profiles.model import OrganizerProfile  # noqa: F401
from app.reviews.model import Review  # noqa: F401


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    configure_celery(app)

    from app.users.controller import bp as users_bp
    from app.events.controller import bp as events_bp
    from app.bookings.controller import bp as bookings_bp
    from app.payments.controller import bp as payments_bp
    from app.organizer_profiles.controller import bp as organizer_profiles_bp
    from app.reviews.controller import bp as reviews_bp

    app.register_blueprint(users_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(organizer_profiles_bp)
    app.register_blueprint(reviews_bp)

    api.register(app)

    @app.errorhandler(TaskEnqueueError)
    def handle_task_enqueue_error(e):
        return error(str(e), 503)

    @app.errorhandler(GatewayError)
    def handle_gateway_error(e):
        return error(str(e), 502)

    # Single catch-all, at the app boundary only — not scattered try/excepts
    # through services/repositories. Anything not handled by a specific
    # handler above (or by ValueError/PermissionError/etc. in a controller)
    # still gets the API's normal JSON envelope instead of a raw Flask/
    # Werkzeug error page. Flask's own routing exceptions (404, 405, ...)
    # pass through unchanged — only genuinely unexpected exceptions are
    # mapped here.
    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        if isinstance(e, HTTPException):
            return e
        app.logger.exception("Unhandled exception")
        return error("internal server error", 500)

    @jwt.unauthorized_loader
    def handle_missing_token(reason):
        return error(reason, 401)

    @jwt.invalid_token_loader
    def handle_invalid_token(reason):
        return error(reason, 422)

    @jwt.expired_token_loader
    def handle_expired_token(jwt_header, jwt_payload):
        return error("token has expired", 401)

    return app
