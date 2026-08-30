import pytest

from app.users.service import AuthService
from app.enums import Role


@pytest.fixture
def auth_service(fake_user_repo):
    return AuthService(user_repository=fake_user_repo)


class TestRegister:
    @pytest.mark.parametrize("role", [Role.CUSTOMER, Role.ORGANIZER])
    def test_register_valid_role_succeeds(self, auth_service, role):
        user = auth_service.register("a@test.com", "555-1234", "pw123", role)

        assert user.email == "a@test.com"
        assert user.role == role
        assert user.password_hash != "pw123"  # never stored in plaintext

    @pytest.mark.parametrize("bad_role", ["admin", "superuser", "", "Organizer"])
    def test_register_invalid_role_raises(self, auth_service, bad_role):
        with pytest.raises(ValueError):
            auth_service.register("a@test.com", None, "pw123", bad_role)

    def test_register_duplicate_email_raises(self, auth_service):
        auth_service.register("dup@test.com", None, "pw123", Role.CUSTOMER)

        with pytest.raises(ValueError, match="already registered"):
            auth_service.register("dup@test.com", None, "pw456", Role.ORGANIZER)


class TestLogin:
    def test_login_correct_credentials_returns_token(self, app, auth_service):
        auth_service.register("a@test.com", None, "correct-pw", Role.CUSTOMER)

        with app.app_context():
            token = auth_service.login("a@test.com", "correct-pw")

        assert isinstance(token, str)
        assert len(token) > 0

    @pytest.mark.parametrize(
        "email,password",
        [
            ("a@test.com", "wrong-pw"),
            ("nonexistent@test.com", "correct-pw"),
        ],
    )
    def test_login_invalid_credentials_raises(self, app, auth_service, email, password):
        auth_service.register("a@test.com", None, "correct-pw", Role.CUSTOMER)

        with app.app_context(), pytest.raises(
            ValueError, match="invalid email or password"
        ):
            auth_service.login(email, password)
