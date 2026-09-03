from abc import abstractmethod

from app.dao_interface import BaseDAO


class IDAO(BaseDAO):
    @abstractmethod
    def get_by_id(self, profile_id): ...

    @abstractmethod
    def get_by_user_id(self, user_id): ...
