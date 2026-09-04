from datetime import datetime, timedelta, timezone

import pytest

from app.organizer_profiles.service import OrganizerProfileService
from app.enums import Role

FUTURE_DATE = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=365)

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


@pytest.fixture
def organizer_profile_service(fake_organizer_profile_repo):
    return OrganizerProfileService(
        organizer_profile_repository=fake_organizer_profile_repo
    )


class TestUpdateProfileService:
    def test_update_nonexistent_profile_raises(self, organizer_profile_service):
        with pytest.raises(ValueError, match="not found"):
            organizer_profile_service.update_profile(999, company_name="New Co")

    def test_update_existing_profile_succeeds(
        self, organizer_profile_service, fake_organizer_profile_repo
    ):
        fake_organizer_profile_repo.create(user_id=5, **ORGANIZER_PROFILE)

        updated = organizer_profile_service.update_profile(5, company_name="New Co")

        assert updated.company_name == "New Co"
        assert updated.city == ORGANIZER_PROFILE["city"]


class TestRegisterEndpoint:
    """HTTP-layer: organizer registration requires the full profile,
    customer registration rejects it."""

    def _payload(self, **overrides):
        payload = {
            "email": "organizer-http@test.com",
            "phone": "555-1234",
            "password": "pw123456",
            "role": Role.ORGANIZER,
            "organizer_profile": ORGANIZER_PROFILE,
        }
        payload.update(overrides)
        return payload

    def test_organizer_without_profile_returns_400(self, client):
        payload = self._payload()
        del payload["organizer_profile"]

        response = client.post("/auth/register", json=payload)

        assert response.status_code == 400

    def test_organizer_with_profile_returns_201_and_persists_profile(self, app, client):
        from app.organizer_profiles.repository import OrganizerProfileRepository

        response = client.post("/auth/register", json=self._payload())

        assert response.status_code == 201
        user_id = response.get_json()["data"]["id"]

        with app.app_context():
            profile = OrganizerProfileRepository().get_by_user_id(user_id)
            assert profile is not None
            assert profile.company_name == ORGANIZER_PROFILE["company_name"]
            assert profile.gst_number is None

    def test_customer_with_organizer_profile_returns_400(self, client):
        response = client.post(
            "/auth/register",
            json={
                "email": "customer-http@test.com",
                "password": "pw123456",
                "role": Role.CUSTOMER,
                "organizer_profile": ORGANIZER_PROFILE,
            },
        )

        assert response.status_code == 400

    def test_organizer_with_gst_number_persists_it(self, app, client):
        from app.organizer_profiles.repository import OrganizerProfileRepository

        payload = self._payload(
            email="organizer-gst@test.com",
            organizer_profile={**ORGANIZER_PROFILE, "gst_number": "22AAAAA0000A1Z5"},
        )

        response = client.post("/auth/register", json=payload)
        user_id = response.get_json()["data"]["id"]

        with app.app_context():
            profile = OrganizerProfileRepository().get_by_user_id(user_id)
            assert profile.gst_number == "22AAAAA0000A1Z5"

    def test_invalid_industry_returns_400(self, client):
        payload = self._payload(
            organizer_profile={**ORGANIZER_PROFILE, "industry": "NOT_A_REAL_INDUSTRY"}
        )

        response = client.post("/auth/register", json=payload)

        assert response.status_code == 400


class TestUpdateProfileEndpoint:
    def test_missing_jwt_returns_401(self, client):
        response = client.patch("/organizers/me", json={"company_name": "New Co"})

        assert response.status_code == 401

    def test_customer_role_forbidden(self, client, register_and_login):
        _, headers = register_and_login(Role.CUSTOMER)

        response = client.patch(
            "/organizers/me", json={"company_name": "New Co"}, headers=headers
        )

        assert response.status_code == 403

    def test_organizer_can_update_own_profile(self, client, register_and_login):
        _, headers = register_and_login(Role.ORGANIZER)

        response = client.patch(
            "/organizers/me", json={"company_name": "Updated Co"}, headers=headers
        )

        assert response.status_code == 200
        assert response.get_json()["data"]["company_name"] == "Updated Co"


class TestEventOrganizerSerialization:
    def test_event_response_includes_organizer_details(
        self, client, register_and_login
    ):
        _, organizer_headers = register_and_login(Role.ORGANIZER)
        created = client.post(
            "/events",
            json={
                "name": "Concert",
                "date": FUTURE_DATE.isoformat(),
                "venue": "Hall A",
                "city": "Bengaluru",
                "capacity": 10,
                "price": "10.00",
            },
            headers=organizer_headers,
        ).get_json()["data"]

        _, customer_headers = register_and_login(Role.CUSTOMER)
        response = client.get(f"/events/{created['id']}", headers=customer_headers)

        organizer = response.get_json()["data"]["organizer"]
        assert organizer["company_name"] == ORGANIZER_PROFILE["company_name"]
        assert organizer["city"] == ORGANIZER_PROFILE["city"]
        assert organizer["industry"] == ORGANIZER_PROFILE["industry"]
        # Sensitive fields must never appear on a customer-facing response.
        assert "pan_number" not in organizer
        assert "bank_account_number" not in organizer
        assert "gst_number" not in organizer
        assert "address" not in organizer
