from flask import Flask, jsonify

from app.config import Config
from app.extensions import db, jwt, configure_celery
from app.exceptions import TaskEnqueueError
from app.docs import api

# Import every domain's model so SQLAlchemy's metadata knows about all
# tables before db.create_all() runs.
from app.users.model import User  # noqa: F401
from app.events.model import Event  # noqa: F401
from app.bookings.model import Booking  # noqa: F401
from app.payments.model import Payment  # noqa: F401
from app.jobs.model import Job  # noqa: F401


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    jwt.init_app(app)
    configure_celery(app)

    from app.users.controller import bp as users_bp
    from app.events.controller import bp as events_bp
    from app.bookings.controller import bp as bookings_bp
    from app.payments.controller import bp as payments_bp

    app.register_blueprint(users_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(bookings_bp)
    app.register_blueprint(payments_bp)

    api.register(app)

    @app.errorhandler(TaskEnqueueError)
    def handle_task_enqueue_error(e):
        return jsonify({"error": "service_unavailable", "message": str(e)}), 503

    with app.app_context():
        db.create_all()

    return app
