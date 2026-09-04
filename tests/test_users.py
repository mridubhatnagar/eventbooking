import pytest

from app.users.service import AuthService
from app.enums import Role


@pytest.fixture
def auth_service(fake_user_repo, fake_organizer_profile_repo):
    return AuthService(
        user_repository=fake_user_repo,
        organizer_profile_repository=fake_organizer_profile_repo,
    )


ORGANIZER_PROFILE = {
    "company_name": "Test Events Co",
    "city": "Bengaluru",
    "address": "123 Test Street, Bengaluru",
    "industry": "MUSIC",
    "pan_number": "ABCDE1234F",
    "bank_account_holder_name": "Test Events Co",
    "bank_account_number": "000123456789",
    "bank_ifsc_code": "TEST0001234",
    "bank_name": "Test Bank",
}


class TestRegister:
    @pytest.mark.parametrize("role", [Role.CUSTOMER, Role.ORGANIZER])
    def test_register_valid_role_succeeds(self, app, auth_service, role):
        organizer_profile = ORGANIZER_PROFILE if role == Role.ORGANIZER else None

        with app.app_context():
            user = auth_service.register(
                "a@test.com", "555-1234", "pw123", role, organizer_profile
            )

        assert user.email == "a@test.com"
        assert user.role == role
        assert user.password_hash != "pw123"  # never stored in plaintext

    @pytest.mark.parametrize("bad_role", ["admin", "superuser", "", "Organizer"])
    def test_register_invalid_role_raises(self, auth_service, bad_role):
        with pytest.raises(ValueError):
            auth_service.register("a@test.com", None, "pw123", bad_role)

    def test_register_duplicate_email_raises(self, app, auth_service):
        with app.app_context():
            auth_service.register("dup@test.com", None, "pw123", Role.CUSTOMER)

            with pytest.raises(ValueError, match="already registered"):
                auth_service.register(
                    "dup@test.com", None, "pw456", Role.ORGANIZER, ORGANIZER_PROFILE
                )

    def test_register_organizer_without_profile_raises(self, app, auth_service):
        with app.app_context(), pytest.raises(TypeError):
            auth_service.register("no-profile@test.com", None, "pw123", Role.ORGANIZER)


class TestLogin:
    def test_login_correct_credentials_returns_token(self, app, auth_service):
        with app.app_context():
            auth_service.register("a@test.com", None, "correct-pw", Role.CUSTOMER)
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
        with app.app_context():
            auth_service.register("a@test.com", None, "correct-pw", Role.CUSTOMER)

            with pytest.raises(ValueError, match="invalid email or password"):
                auth_service.login(email, password)


class TestRegisterEndpoint:
    """HTTP-layer: routing, request validation, response shape."""

    def test_register_returns_201_with_user(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "http-register@test.com",
                "phone": "555-1234",
                "password": "pw123456",
                "role": Role.CUSTOMER,
            },
        )

        assert response.status_code == 201
        body = response.get_json()["data"]
        assert body["email"] == "http-register@test.com"
        assert body["role"] == Role.CUSTOMER

    @pytest.mark.parametrize(
        "bad_email",
        ["not-an-email", "missing-domain@", "@missing-local.com", "no-at-sign.com", ""],
    )
    def test_register_invalid_email_returns_400(self, client, bad_email):
        response = client.post(
            "/auth/register",
            json={
                "email": bad_email,
                "phone": "555-1234",
                "password": "pw123456",
                "role": Role.CUSTOMER,
            },
        )

        assert response.status_code == 400

    @pytest.mark.parametrize("short_password", ["", "a", "1234567"])
    def test_register_short_password_returns_400(self, client, short_password):
        response = client.post(
            "/auth/register",
            json={
                "email": "short-pw@test.com",
                "password": short_password,
                "role": Role.CUSTOMER,
            },
        )

        assert response.status_code == 400

    def test_register_missing_required_field_returns_400(self, client):
        response = client.post(
            "/auth/register", json={"email": "no-password@test.com", "role": "customer"}
        )

        assert response.status_code == 400

    def test_register_invalid_role_returns_400(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "bad-role@test.com",
                "password": "pw123456",
                "role": "admin",
            },
        )

        assert response.status_code == 400

    def test_register_duplicate_email_returns_400(self, client):
        payload = {
            "email": "dup-http@test.com",
            "password": "pw123456",
            "role": Role.CUSTOMER,
        }
        first = client.post("/auth/register", json=payload)
        assert first.status_code == 201

        second = client.post("/auth/register", json=payload)
        assert second.status_code == 400


class TestLoginEndpoint:
    def test_login_returns_access_token(self, client):
        client.post(
            "/auth/register",
            json={
                "email": "http-login@test.com",
                "password": "correct-pw",
                "role": Role.CUSTOMER,
            },
        )

        response = client.post(
            "/auth/login",
            json={"email": "http-login@test.com", "password": "correct-pw"},
        )

        assert response.status_code == 200
        assert response.get_json()["data"]["access_token"]

    def test_login_wrong_password_returns_401(self, client):
        client.post(
            "/auth/register",
            json={
                "email": "http-login-2@test.com",
                "password": "correct-pw",
                "role": Role.CUSTOMER,
            },
        )

        response = client.post(
            "/auth/login",
            json={"email": "http-login-2@test.com", "password": "wrong-pw"},
        )

        assert response.status_code == 401

    def test_login_invalid_email_format_returns_400(self, client):
        response = client.post(
            "/auth/login",
            json={"email": "not-an-email", "password": "correct-pw"},
        )

        assert response.status_code == 400
