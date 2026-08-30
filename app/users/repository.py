from app.extensions import db
from app.users.model import User
from app.users.dao_interface import IDAO


class UserRepository(IDAO):
    def get_by_id(self, user_id):
        return db.session.get(User, user_id)

    def get_by_email(self, email):
        return User.query.filter_by(email=email).first()

    def create(self, **kwargs):
        user = User(**kwargs)
        db.session.add(user)
        db.session.commit()
        return user

    def update(self, id, **kwargs):
        user = self.get_by_id(id)
        if not user:
            return None
        for key, value in kwargs.items():
            setattr(user, key, value)
        db.session.commit()
        return user

    def list(self, **filters):
        return User.query.filter_by(**filters).all()
