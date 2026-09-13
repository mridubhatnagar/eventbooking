from flask import current_app

from app.extensions import celery
from app.bookings.repository import BookingRepository
from app.users.repository import UserRepository
from app.jobs.repository import JobRepository
from app.enums import BookingStatus, JobStatus


@celery.task(bind=True, name="events.notify_event_update")
def notify_event_update(self, event_id):
    """Background Task 2 (frozen in PLAN.md): notify customers with a
    CONFIRMED booking for this event — i.e. payment has actually succeeded,
    not just been attempted. A PENDING booking's payment could still resolve
    to FAILED, so notifying on PENDING would risk telling someone about an
    update to an event they never actually paid for. Console log only for
    this assignment."""
    job_repository = JobRepository()
    job = job_repository.create(
        task_id=self.request.id,
        task_name=self.name,
        status=JobStatus.STARTED,
        event_id=event_id,
    )

    booking_repository = BookingRepository()
    user_repository = UserRepository()

    bookings = booking_repository.list(event_id=event_id)
    for booking in bookings:
        if booking.status != BookingStatus.CONFIRMED:
            continue
        user = user_repository.get_by_id(booking.user_id)
        current_app.logger.info("Event %s updated — notifying %s", event_id, user.email)

    job_repository.update(job.id, status=JobStatus.SUCCESS)
