import os
from datetime import timedelta


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(
        days=int(os.environ.get("JWT_EXPIRY_DAYS", 2))
    )

    CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://redis:6379/0")

    RAZORPAY_MODE = os.environ.get("RAZORPAY_MODE", "test")
    RAZORPAY_KEY_ID = os.environ.get(f"RAZORPAY_{RAZORPAY_MODE.upper()}_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.environ.get(
        f"RAZORPAY_{RAZORPAY_MODE.upper()}_KEY_SECRET", ""
    )
    RAZORPAY_WEBHOOK_SECRET = os.environ["RAZORPAY_WEBHOOK_SECRET"]

    MOCK_TRIGGER_API_KEY = os.environ["MOCK_TRIGGER_API_KEY"]
    WEB_BASE_URL = os.environ.get("WEB_BASE_URL", "http://web:5000")

    PAYMENT_GATEWAY_DELAY_SECONDS = int(
        os.environ.get("PAYMENT_GATEWAY_DELAY_SECONDS", 5)
    )
