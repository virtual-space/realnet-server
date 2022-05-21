from abc import ABC, abstractmethod


class Module(ABC):

    @abstractmethod
    def get_item(self, id):
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

    @abstractmethod
    def create_item(self, parent_item=None, **kwargs):
        pass

    @abstractmethod
    def get_item_data(self, item):
        pass

    @abstractmethod
    def update_item_data(self, item, storage):
        pass

    @abstractmethod
    def delete_item_data(self, item):
        pass

    @abstractmethod
    def perform_search(self, id, account, data, public):
        pass

    @abstractmethod
    def invoke(self, item, arguments):
        pass

    @abstractmethod
    def message(self, item, arguments):
        pass

    @abstractmethod
    def import_file(self, item, file):
        pass

