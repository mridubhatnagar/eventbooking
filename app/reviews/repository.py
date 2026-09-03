from app.extensions import db
from app.reviews.model import Review
from app.reviews.dao_interface import IDAO


class ReviewRepository(IDAO):
    def get_by_id(self, review_id):
        return db.session.get(Review, review_id)

    def get_by_booking_id(self, booking_id):
        return Review.query.filter_by(booking_id=booking_id).first()

    def create(self, **kwargs):
        review = Review(**kwargs)
        db.session.add(review)
        db.session.commit()
        return review

    def update(self, id, **kwargs):
        review = self.get_by_id(id)
        if not review:
            return None
        for key, value in kwargs.items():
            setattr(review, key, value)
        db.session.commit()
        return review

    def list(self, **filters):
        return Review.query.filter_by(**filters).all()
