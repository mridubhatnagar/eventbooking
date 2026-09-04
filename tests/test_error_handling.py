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

        response = client.get("/events/1", headers=headers)

        assert response.status_code == 500
        body = response.get_json()
        assert body["data"] is None
        assert "error" in body

    def test_routing_404_is_untouched(self, client):
        response = client.get("/this-route-does-not-exist")

        assert response.status_code == 404
