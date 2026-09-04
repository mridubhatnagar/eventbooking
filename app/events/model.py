from app.extensions import db
from app.base import TimestampMixin


class Event(db.Model, TimestampMixin):
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, index=True
    )
    name = db.Column(db.String(255), nullable=False)
    date = db.Column(db.DateTime, nullable=False, index=True)
    venue = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(255), nullable=False, index=True)
    capacity = db.Column(db.Integer, nullable=False)
    tickets_sold = db.Column(db.Integer, nullable=False, default=0)
    price = db.Column(db.Numeric(10, 2), nullable=False)

    @property
    def capacity_remaining(self):
        return self.capacity - self.tickets_sold
