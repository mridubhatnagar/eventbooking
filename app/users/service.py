from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

from app.extensions import db
from app.users.repository import UserRepository
from app.organizer_profiles.repository import OrganizerProfileRepository
from app.enums import Role


class AuthService:
    def __init__(self, user_repository=None, organizer_profile_repository=None):
        self.user_repository = user_repository or UserRepository()
        self.organizer_profile_repository = (
            organizer_profile_repository or OrganizerProfileRepository()
        )

    def register(self, email, phone, password, role, organizer_profile=None):
        if role not in set(Role):
            raise ValueError(f"role must be one of {sorted(Role)}")
        if self.user_repository.get_by_email(email):
            raise ValueError("email already registered")

        password_hash = generate_password_hash(password)

        # Both writes share one transaction: an organizer without a profile
        # (or vice versa) should never be possible.
        try:
            user = self.user_repository.create(
                commit=False,
                email=email,
                phone=phone,
                password_hash=password_hash,
                role=role,
            )
            if role == Role.ORGANIZER:
                self.organizer_profile_repository.create(
                    commit=False, user_id=user.id, **organizer_profile
                )
            db.session.commit()
        except Exception:
            db.session.rollback()
            raise

        return user

    def login(self, email, password):
        user = self.user_repository.get_by_email(email)
        if not user or not check_password_hash(user.password_hash, password):
            raise ValueError("invalid email or password")

        return create_access_token(
            identity=str(user.id), additional_claims={"role": user.role}
        )
