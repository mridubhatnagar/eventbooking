import requests
from flask import current_app

from app.extensions import celery
from app.payments.repository import PaymentRepository
from app.jobs.repository import JobRepository
from app.enums import GatewayStatus, JobStatus, PaymentStatus, WebhookEvent


@celery.task(bind=True, name="payments.request_payment")
def request_payment(self, payment_id):
    """Payment Flow step 2 (frozen in PLAN.md): sets status=REQUESTED,
    gateway_status=captured. Schedules the delayed gateway callback trigger
    to simulate processing latency."""
    job_repository = JobRepository()
    job = job_repository.create(
        task_id=self.request.id,
        task_name=self.name,
        status=JobStatus.STARTED,
        payment_id=payment_id,
    )

    payment = PaymentRepository().update(
        payment_id,
        status=PaymentStatus.REQUESTED,
        gateway_status=GatewayStatus.CAPTURED,
    )

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
        f"{current_app.config['WEB_BASE_URL']}/mock/razorpay/simulate-webhook",
        json={"order_id": order_id, "event": event_type},
        headers={"x-api-key": current_app.config["MOCK_TRIGGER_API_KEY"]},
        timeout=10,
    )

    job_repository.update(
        job.id, status=JobStatus.SUCCESS if response.ok else JobStatus.FAILED
    )
