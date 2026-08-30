from app.extensions import db
from app.payments.model import Payment
from app.payments.dao_interface import IDAO


class PaymentRepository(IDAO):
    def get_by_id(self, payment_id):
        return db.session.get(Payment, payment_id)

    def get_by_order_id(self, order_id):
        return Payment.query.filter_by(order_id=order_id).first()

    def get_by_booking_id(self, booking_id):
        return Payment.query.filter_by(booking_id=booking_id).first()

    def create(self, commit=True, **kwargs):
        payment = Payment(**kwargs)
        db.session.add(payment)
        if commit:
            db.session.commit()
        else:
            db.session.flush()
        return payment

    def update(self, id, **kwargs):
        payment = self.get_by_id(id)
        if not payment:
            return None
        for key, value in kwargs.items():
            setattr(payment, key, value)
        db.session.commit()
        return payment

    def list(self, **filters):
        return Payment.query.filter_by(**filters).all()
