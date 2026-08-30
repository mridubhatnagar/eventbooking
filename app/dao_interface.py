from abc import ABC, abstractmethod


class BaseDAO(ABC):
    """Generic contract every domain's DAO/Repository implements."""

    @abstractmethod
    def create(self, **kwargs):
        ...

    @abstractmethod
    def update(self, id, **kwargs):
        ...

    @abstractmethod
    def list(self, **filters):
        ...
