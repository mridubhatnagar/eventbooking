from app.extensions import celery
from app.bookings.repository import BookingRepository
from app.users.repository import UserRepository
from app.jobs.repository import JobRepository
from app.enums import JobStatus


@celery.task(bind=True, name="events.notify_event_update")
def notify_event_update(self, event_id):
    """Background Task 2 (frozen in PLAN.md): notify all customers who
    booked tickets for this event. Console log only for this assignment."""
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
        user = user_repository.get_by_id(booking.user_id)
        print(f"[notification] Event {event_id} updated — notifying {user.email}")

    job_repository.update(job.id, status=JobStatus.SUCCESS)
