from flask import current_app

from app.extensions import celery
from app.bookings.repository import BookingRepository
from app.users.repository import UserRepository
from app.jobs.repository import JobRepository
from app.enums import JobStatus


@celery.task(bind=True, name="bookings.send_booking_confirmation")
def send_booking_confirmation(self, booking_id, payment_id=None):
    """Background Task 1 (frozen in PLAN.md): fires only once Payment reaches
    PROCESSED. Console log only for this assignment."""
    job_repository = JobRepository()
    job = job_repository.create(
        task_id=self.request.id,
        task_name=self.name,
        status=JobStatus.STARTED,
        payment_id=payment_id,
    )

    booking = BookingRepository().get_by_id(booking_id)
    user = UserRepository().get_by_id(booking.user_id)
    current_app.logger.info(
        "Booking confirmation sent to %s for booking %s", user.email, booking_id
    )

    job_repository.update(job.id, status=JobStatus.SUCCESS)
