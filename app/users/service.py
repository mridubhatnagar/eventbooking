from werkzeug.security import generate_password_hash, check_password_hash
from flask_jwt_extended import create_access_token

from app.users.repository import UserRepository
from app.enums import Role


class AuthService:
    def __init__(self, user_repository=None):
        self.user_repository = user_repository or UserRepository()

    def register(self, email, phone, password, role):
        if role not in set(Role):
            raise ValueError(f"role must be one of {sorted(Role)}")
        if self.user_repository.get_by_email(email):
            raise ValueError("email already registered")

        password_hash = generate_password_hash(password)
        return self.user_repository.create(
            email=email, phone=phone, password_hash=password_hash, role=role
        )

    def login(self, email, password):
        user = self.user_repository.get_by_email(email)
        if not user or not check_password_hash(user.password_hash, password):
            raise ValueError("invalid email or password")

        return create_access_token(
            identity=str(user.id), additional_claims={"role": user.role}
        )
