from abc import ABC, abstractmethod


class Module(ABC):

    @abstractmethod
    def get_item(self, item):
        pass

    @abstractmethod
    def get_items(self, item):
        pass

    @abstractmethod
    def delete_item(self, item):
        pass

    @abstractmethod
    def update_item(self, item, **kwargs):
        pass

