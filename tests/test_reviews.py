from datetime import datetime

import pytest

from app.reviews.service import ReviewService
from app.enums import GatewayStatus, PaymentStatus, Role

PAST_DATE = datetime(2020, 1, 1, 18, 0)
FUTURE_DATE = datetime(2099, 1, 1, 18, 0)


@pytest.fixture
def review_service(
    fake_review_repo, fake_booking_repo, fake_payment_repo, fake_event_repo
):
    return ReviewService(
        review_repository=fake_review_repo,
        booking_repository=fake_booking_repo,
        payment_repository=fake_payment_repo,
        event_repository=fake_event_repo,
    )


def _seed_event(fake_event_repo, date=PAST_DATE):
    return fake_event_repo.create(
        user_id=1,
        name="Concert",
        date=date,
        venue="Hall A",
        city="Bengaluru",
        capacity=10,
        tickets_sold=1,
        price=10,
    )


def _seed_booking(fake_booking_repo, event_id, user_id=5):
    return fake_booking_repo.create(user_id=user_id, event_id=event_id, quantity=1)


def _seed_payment(fake_payment_repo, booking_id, status=PaymentStatus.PROCESSED):
    return fake_payment_repo.create(
        booking_id=booking_id,
        amount=10,
        order_id=f"order-{booking_id}",
        gateway_status=GatewayStatus.CAPTURED,
        status=status,
    )


class TestCreateReviewService:
    def test_booking_not_found_raises_lookup_error(self, review_service):
        with pytest.raises(LookupError):
            review_service.create_review(999, user_id=5, rating=5)

    def test_booking_not_owned_raises_lookup_error(
        self, review_service, fake_event_repo, fake_booking_repo
    ):
        event = _seed_event(fake_event_repo)
        booking = _seed_booking(fake_booking_repo, event.id, user_id=5)

        with pytest.raises(LookupError):
            review_service.create_review(booking.id, user_id=999, rating=5)

    def test_unpaid_booking_raises_value_error(
        self, review_service, fake_event_repo, fake_booking_repo, fake_payment_repo
    ):
        event = _seed_event(fake_event_repo)
        booking = _seed_booking(fake_booking_repo, event.id)
        _seed_payment(fake_payment_repo, booking.id, status=PaymentStatus.PENDING)

        with pytest.raises(ValueError, match="confirmed"):
            review_service.create_review(booking.id, user_id=5, rating=5)

    def test_booking_with_no_payment_raises_value_error(
        self, review_service, fake_event_repo, fake_booking_repo
    ):
        event = _seed_event(fake_event_repo)
        booking = _seed_booking(fake_booking_repo, event.id)

        with pytest.raises(ValueError, match="confirmed"):
            review_service.create_review(booking.id, user_id=5, rating=5)

    def test_future_event_raises_value_error(
        self, review_service, fake_event_repo, fake_booking_repo, fake_payment_repo
    ):
        event = _seed_event(fake_event_repo, date=FUTURE_DATE)
        booking = _seed_booking(fake_booking_repo, event.id)
        _seed_payment(fake_payment_repo, booking.id)

        with pytest.raises(ValueError, match="not taken place"):
            review_service.create_review(booking.id, user_id=5, rating=5)

    def test_duplicate_review_raises_value_error(
        self, review_service, fake_event_repo, fake_booking_repo, fake_payment_repo
    ):
        event = _seed_event(fake_event_repo)
        booking = _seed_booking(fake_booking_repo, event.id)
        _seed_payment(fake_payment_repo, booking.id)

        review_service.create_review(booking.id, user_id=5, rating=5)

        with pytest.raises(ValueError, match="already reviewed"):
            review_service.create_review(booking.id, user_id=5, rating=3)

    def test_valid_review_is_created(
        self, review_service, fake_event_repo, fake_booking_repo, fake_payment_repo
    ):
        event = _seed_event(fake_event_repo)
        booking = _seed_booking(fake_booking_repo, event.id)
        _seed_payment(fake_payment_repo, booking.id)

        review = review_service.create_review(
            booking.id, user_id=5, rating=4, review_text="Great show"
        )

        assert review.rating == 4
        assert review.review_text == "Great show"
        assert review.booking_id == booking.id


class TestListForEventService:
    def test_only_returns_reviews_for_that_event(
        self, review_service, fake_event_repo, fake_booking_repo, fake_payment_repo
    ):
        event_a = _seed_event(fake_event_repo)
        event_b = _seed_event(fake_event_repo)
        booking_a = _seed_booking(fake_booking_repo, event_a.id)
        booking_b = _seed_booking(fake_booking_repo, event_b.id)
        _seed_payment(fake_payment_repo, booking_a.id)
        _seed_payment(fake_payment_repo, booking_b.id)
        review_service.create_review(booking_a.id, user_id=5, rating=5)
        review_service.create_review(booking_b.id, user_id=5, rating=1)

        reviews = review_service.list_for_event(event_a.id)

        assert len(reviews) == 1
        assert reviews[0].rating == 5

    def test_unreviewed_bookings_are_skipped(
        self, review_service, fake_event_repo, fake_booking_repo, fake_payment_repo
    ):
        event = _seed_event(fake_event_repo)
        _seed_booking(fake_booking_repo, event.id)  # never reviewed

        reviews = review_service.list_for_event(event.id)

        assert reviews == []


def _setup_confirmed_past_booking(app, customer_id, organizer_id=1, date=PAST_DATE):
    from app.events.repository import EventRepository
    from app.bookings.repository import BookingRepository
    from app.payments.repository import PaymentRepository

    with app.app_context():
        event = EventRepository().create(
            user_id=organizer_id,
            name="Concert",
            date=date,
            venue="Hall A",
            city="Bengaluru",
            capacity=10,
            tickets_sold=1,
            price=10,
        )
        booking = BookingRepository().create(
            user_id=customer_id, event_id=event.id, quantity=1
        )
        PaymentRepository().create(
            booking_id=booking.id,
            amount=10,
            order_id=f"order-{booking.id}",
            gateway_status=GatewayStatus.CAPTURED,
            status=PaymentStatus.PROCESSED,
        )
        return event.id, booking.id


class TestCreateReviewEndpoint:
    def test_missing_jwt_returns_401(self, client):
        response = client.post("/bookings/1/reviews", json={"rating": 5})

        assert response.status_code == 401

    def test_organizer_role_forbidden(self, client, register_and_login):
        _, headers = register_and_login(Role.ORGANIZER)

        response = client.post(
            "/bookings/1/reviews", json={"rating": 5}, headers=headers
        )

        assert response.status_code == 403

    def test_owner_can_review_confirmed_past_booking(
        self, app, client, register_and_login
    ):
        customer_id, headers = register_and_login(Role.CUSTOMER)
        _, booking_id = _setup_confirmed_past_booking(app, customer_id)

        response = client.post(
            f"/bookings/{booking_id}/reviews",
            json={"rating": 5, "review_text": "Great show"},
            headers=headers,
        )

        assert response.status_code == 201
        body = response.get_json()["data"]
        assert body["rating"] == 5
        assert body["review_text"] == "Great show"

    def test_non_owner_gets_404(self, app, client, register_and_login):
        owner_id, _ = register_and_login(Role.CUSTOMER)
        _, booking_id = _setup_confirmed_past_booking(app, owner_id)

        _, other_headers = register_and_login(Role.CUSTOMER)
        response = client.post(
            f"/bookings/{booking_id}/reviews", json={"rating": 5}, headers=other_headers
        )

        assert response.status_code == 404

    def test_unconfirmed_booking_returns_400(self, app, client, register_and_login):
        from app.events.repository import EventRepository
        from app.bookings.repository import BookingRepository

        customer_id, headers = register_and_login(Role.CUSTOMER)
        with app.app_context():
            event = EventRepository().create(
                user_id=1,
                name="Concert",
                date=PAST_DATE,
                venue="Hall A",
                city="Bengaluru",
                capacity=10,
                tickets_sold=1,
                price=10,
            )
            booking = BookingRepository().create(
                user_id=customer_id, event_id=event.id, quantity=1
            )
            booking_id = booking.id

        response = client.post(
            f"/bookings/{booking_id}/reviews", json={"rating": 5}, headers=headers
        )

        assert response.status_code == 400

    def test_future_event_returns_400(self, app, client, register_and_login):
        customer_id, headers = register_and_login(Role.CUSTOMER)
        _, booking_id = _setup_confirmed_past_booking(
            app, customer_id, date=FUTURE_DATE
        )

        response = client.post(
            f"/bookings/{booking_id}/reviews", json={"rating": 5}, headers=headers
        )

        assert response.status_code == 400

    def test_duplicate_review_returns_400(self, app, client, register_and_login):
        customer_id, headers = register_and_login(Role.CUSTOMER)
        _, booking_id = _setup_confirmed_past_booking(app, customer_id)

        first = client.post(
            f"/bookings/{booking_id}/reviews", json={"rating": 5}, headers=headers
        )
        assert first.status_code == 201

        second = client.post(
            f"/bookings/{booking_id}/reviews", json={"rating": 3}, headers=headers
        )
        assert second.status_code == 400

    @pytest.mark.parametrize("rating", [0, 6])
    def test_rating_out_of_range_returns_400(
        self, app, client, register_and_login, rating
    ):
        customer_id, headers = register_and_login(Role.CUSTOMER)
        _, booking_id = _setup_confirmed_past_booking(app, customer_id)

        response = client.post(
            f"/bookings/{booking_id}/reviews", json={"rating": rating}, headers=headers
        )

        assert response.status_code == 400


class TestListEventReviewsEndpoint:
    def test_missing_jwt_returns_401(self, client):
        response = client.get("/events/1/reviews")

        assert response.status_code == 401

    def test_nonexistent_event_returns_404(self, client, register_and_login):
        _, headers = register_and_login(Role.CUSTOMER)

        response = client.get("/events/999999/reviews", headers=headers)

        assert response.status_code == 404

    def test_any_authenticated_role_can_list_reviews(
        self, app, client, register_and_login
    ):
        customer_id, customer_headers = register_and_login(Role.CUSTOMER)
        event_id, booking_id = _setup_confirmed_past_booking(app, customer_id)
        client.post(
            f"/bookings/{booking_id}/reviews",
            json={"rating": 4, "review_text": "Nice"},
            headers=customer_headers,
        )

        _, organizer_headers = register_and_login(Role.ORGANIZER)
        response = client.get(f"/events/{event_id}/reviews", headers=organizer_headers)

        assert response.status_code == 200
        reviews = response.get_json()["data"]
        assert len(reviews) == 1
        assert reviews[0]["rating"] == 4
