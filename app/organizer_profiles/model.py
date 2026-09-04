from app.extensions import db
from app.base import TimestampMixin


class OrganizerProfile(db.Model, TimestampMixin):
    __tablename__ = "organizer_profiles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(
        db.Integer, db.ForeignKey("users.id"), nullable=False, unique=True
    )
    company_name = db.Column(db.String(255), nullable=False)
    city = db.Column(db.String(255), nullable=False)
    address = db.Column(db.String(500), nullable=False)
    industry = db.Column(db.String(30), nullable=False)
    gst_number = db.Column(db.String(20), nullable=True)
    pan_number = db.Column(db.String(20), nullable=False)
    bank_account_holder_name = db.Column(db.String(255), nullable=False)
    bank_account_number = db.Column(db.String(34), nullable=False)
    bank_ifsc_code = db.Column(db.String(11), nullable=False)
    bank_name = db.Column(db.String(255), nullable=False)

    # Cross-domain relationship resolved by class name string (no import needed,
    # avoids coupling organizer_profiles to the users module directly).
    user = db.relationship(
        "User", backref=db.backref("organizer_profile", uselist=False), lazy=True
    )
