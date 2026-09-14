"""App-level concern (app/__init__.py's catch-all error handler), not tied
to one domain — hence its own file rather than living in a domain's test
module."""

from app.enums import Role


class TestUnexpectedErrorHandler:
    def test_unexpected_exception_returns_consistent_json_envelope(
        self, client, register_and_login, monkeypatch
    ):
        _, headers = register_and_login(Role.CUSTOMER)
        monkeypatch.setattr(
            "app.events.service.EventService.get_event",
            lambda self, event_id: (_ for _ in ()).throw(RuntimeError("boom")),
        )

        response = client.get("/v1/events/1", headers=headers)

        assert response.status_code == 500
        body = response.get_json()
        assert body["data"] is None
        assert "error" in body

    def test_routing_404_is_untouched(self, client):
        response = client.get("/this-route-does-not-exist")

        assert response.status_code == 404


class TestIndexRoute:
    def test_root_returns_rendered_readme(self, client):
        response = client.get("/")

        assert response.status_code == 200
        assert response.content_type.startswith("text/html")
        body = response.get_data(as_text=True)
        assert "Event Booking System" in body
        assert "<h1>" in body


class TestHealthRoute:
    def test_healthy_when_db_reachable(self, client):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.get_json()["data"]["status"] == "ok"

    def test_unhealthy_when_db_unreachable(self, client, monkeypatch):
        from sqlalchemy.orm import Session

        def _boom(*a, **kw):
            raise RuntimeError("connection refused")

        # Patch the Session class itself, not a resolved db.session instance —
        # Flask-SQLAlchemy's session is scoped per app/request context, so an
        # instance-level patch made outside the test client's own request
        # context could silently miss the actual session the view uses.
        monkeypatch.setattr(Session, "execute", _boom)

        response = client.get("/health")

        assert response.status_code == 503
        assert response.get_json()["data"] is None
