from app.extensions import db
from app.base import TimestampMixin


class Job(db.Model, TimestampMixin):
    """Generic audit log of every Celery task run. DB-queryable only — no API exposure."""

    __tablename__ = "jobs"

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.String(64), nullable=False, index=True)
    task_name = db.Column(db.String(128), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    event_id = db.Column(db.Integer, db.ForeignKey("events.id"), nullable=True)
    payment_id = db.Column(db.Integer, db.ForeignKey("payments.id"), nullable=True)
