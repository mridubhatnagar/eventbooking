from abc import abstractmethod

from app.dao_interface import BaseDAO


class IDAO(BaseDAO):
    @abstractmethod
    def get_by_id(self, review_id): ...

    @abstractmethod
    def get_by_booking_id(self, booking_id): ...
