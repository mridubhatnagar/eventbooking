from app.extensions import db
from app.organizer_profiles.model import OrganizerProfile
from app.organizer_profiles.dao_interface import IDAO


class OrganizerProfileRepository(IDAO):
    def get_by_id(self, profile_id):
        return db.session.get(OrganizerProfile, profile_id)

    def get_by_user_id(self, user_id):
        return OrganizerProfile.query.filter_by(user_id=user_id).first()

    def create(self, commit=True, **kwargs):
        profile = OrganizerProfile(**kwargs)
        db.session.add(profile)
        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return profile

    def update(self, id, **kwargs):
        profile = self.get_by_id(id)
        if not profile:
            return None
        for key, value in kwargs.items():
            setattr(profile, key, value)
        db.session.commit()
        return profile

    def list(self, **filters):
        return OrganizerProfile.query.filter_by(**filters).all()
