import requests
from flask import current_app

from app.extensions import celery
from app.payments.repository import PaymentRepository
from app.jobs.repository import JobRepository
from app.enums import JobStatus, WebhookEvent


@celery.task(bind=True, name="payments.request_payment")
def request_payment(self, payment_id):
    """Payment Flow step 2: the entry point for the async side of a booking's
    payment. Razorpay auto-captures by default (see decisions.md) — there is
    no separate merchant-initiated capture call, so this task does no
    gateway work itself. It exists as its own task (rather than having
    bookings/service.py schedule trigger_gateway_callback directly) purely
    to keep payments-internal scheduling details (the countdown, the event
    type) out of the bookings domain. Payment stays PENDING until the
    webhook arrives. Schedules the delayed gateway callback trigger to
    simulate real-world gateway processing latency."""
    job_repository = JobRepository()
    job = job_repository.create(
        task_id=self.request.id,
        task_name=self.name,
        status=JobStatus.STARTED,
        payment_id=payment_id,
    )

    payment = PaymentRepository().get_by_id(payment_id)

    job_repository.update(job.id, status=JobStatus.SUCCESS)

    trigger_gateway_callback.apply_async(
        args=[payment.order_id, WebhookEvent.PAYMENT_CAPTURED],
        countdown=current_app.config["PAYMENT_GATEWAY_DELAY_SECONDS"],
    )


@celery.task(bind=True, name="payments.trigger_gateway_callback")
def trigger_gateway_callback(self, order_id, event_type):
    """Payment Flow step 3 (frozen in PLAN.md): calls the mock trigger
    endpoint, which builds a signed fake event and calls the real webhook
    receiver — the only throwaway piece in the flow."""
    job_repository = JobRepository()
    job = job_repository.create(
        task_id=self.request.id, task_name=self.name, status=JobStatus.STARTED
    )

    response = requests.post(
        f"{current_app.config['RAZORPAY_MOCK_BASE_URL']}/mock/razorpay/simulate-webhook",
        json={"order_id": order_id, "event": event_type},
        headers={"x-api-key": current_app.config["MOCK_TRIGGER_API_KEY"]},
        timeout=10,
    )

    if not response.ok:
        current_app.logger.error(
            "mock trigger webhook call failed for order %s: %s %s",
            order_id,
            response.status_code,
            response.text,
        )

    job_repository.update(
        job.id, status=JobStatus.SUCCESS if response.ok else JobStatus.FAILED
    )
