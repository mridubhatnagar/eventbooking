from celery import Celery
from flask import has_app_context
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()
celery = Celery(__name__)


def configure_celery(app):
    """Binds the shared Celery app to Flask's app context so tasks can use
    db.session etc. Called once from the app factory.

    Task functions are decorated with @celery.task at *module import time*,
    which bakes in whatever celery.Task class is active at that moment —
    reassigning celery.Task later (here, on a later configure_celery() call)
    does not retroactively change already-decorated tasks. In production
    there's only ever one app, so this is invisible. But create_app() runs
    once per test, and Python only imports each task module once per
    process — so every test after the first would otherwise run tasks
    against the *first* test's app/DB, not its own, whenever a test invokes
    a task while already inside its own app context. has_app_context()
    below fixes that: reuse whatever context the caller already pushed
    (always true when running under test) and only fall back to pushing
    this ContextTask's own closured app (the real, single production app)
    when none is active — the real worker-process scenario.
    """
    celery.conf.update(
        broker_url=app.config["CELERY_BROKER_URL"],
        result_backend=app.config["CELERY_RESULT_BACKEND"],
    )

    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            if has_app_context():
                return self.run(*args, **kwargs)
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
