from abc import ABC, abstractmethod


class Item(ABC):

    @abstractmethod
    def get_items(self):
        return []

    @abstractmethod
    def get_id(self):
        return None

    @abstractmethod
    def get_name(self):
        return None

    @abstractmethod
    def get_properties(self):
        return None

    @abstractmethod
    def get_data(self):
        return None

    def get_representation(self):
        return {
            'name': self.get_name(),
            'id': self.get_id(),
            'items': [i.get_representation() for i in self.get_items() if i is not None]
        }
