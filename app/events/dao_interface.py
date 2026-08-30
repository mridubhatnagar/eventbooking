from abc import abstractmethod

from app.dao_interface import BaseDAO


class IDAO(BaseDAO):
    @abstractmethod
    def get_by_id(self, event_id):
        ...
