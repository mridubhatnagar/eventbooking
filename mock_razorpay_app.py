"""WSGI entrypoint for the mock Razorpay service — a separate process from
the real app (see app/payments/mock_controller.py for why). No DB/JWT/Celery
wiring needed: these endpoints are stateless."""

from flask import Flask

from app.config import Config
from app.payments.mock_controller import bp as mock_razorpay_bp


def create_mock_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.register_blueprint(mock_razorpay_bp)
    return app


app = create_mock_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
