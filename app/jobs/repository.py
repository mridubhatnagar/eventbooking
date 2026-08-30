from app.extensions import db
from app.jobs.model import Job
from app.jobs.dao_interface import IDAO


class JobRepository(IDAO):
    """DB-queryable only (frozen in PLAN.md) — no controller/API exposure for this domain."""

    def get_by_id(self, job_id):
        return db.session.get(Job, job_id)

    def create(self, **kwargs):
        job = Job(**kwargs)
        db.session.add(job)
        db.session.commit()
        return job

    def update(self, id, **kwargs):
        job = self.get_by_id(id)
        if not job:
            return None
        for key, value in kwargs.items():
            setattr(job, key, value)
        db.session.commit()
        return job

    def list(self, **filters):
        return Job.query.filter_by(**filters).all()
