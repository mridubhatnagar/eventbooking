import os
from datetime import timedelta


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ["DATABASE_URL"]
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    JWT_SECRET_KEY = os.environ["JWT_SECRET_KEY"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(days=int(os.environ.get("JWT_EXPIRY_DAYS", 2)))

    CELERY_BROKER_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://redis:6379/0")

    RAZORPAY_MODE = os.environ.get("RAZORPAY_MODE", "test")
    RAZORPAY_KEY_ID = os.environ.get(f"RAZORPAY_{RAZORPAY_MODE.upper()}_KEY_ID", "")
    RAZORPAY_KEY_SECRET = os.environ.get(
        f"RAZORPAY_{RAZORPAY_MODE.upper()}_KEY_SECRET", ""
    )
    RAZORPAY_WEBHOOK_SECRET = os.environ["RAZORPAY_WEBHOOK_SECRET"]

    MOCK_TRIGGER_API_KEY = os.environ["MOCK_TRIGGER_API_KEY"]
    WEB_BASE_URL = os.environ.get("WEB_BASE_URL", "http://app:5000")
    RAZORPAY_MOCK_BASE_URL = os.environ.get(
        "RAZORPAY_MOCK_BASE_URL", "http://mock-razorpay:5000"
    )

    PAYMENT_GATEWAY_DELAY_SECONDS = int(
        os.environ.get("PAYMENT_GATEWAY_DELAY_SECONDS", 5)
    )

    REDIS_URL = os.environ.get("REDIS_URL", "redis://redis:6379/0")

    # Rate limiting (decision 29). Reuses the existing Redis instance as the
    # counter store — separate from REDIS_URL so tests can point it at an
    # in-process memory:// store without touching Celery's broker config.
    RATELIMIT_ENABLED = os.environ.get("RATELIMIT_ENABLED", "true").lower() == "true"
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", REDIS_URL)
    RATELIMIT_DEFAULT = ["200 per day", "50 per hour"]
