from abc import ABC, abstractmethod
import hashlib

class Item(ABC):

    @abstractmethod
    def get_items(self):
        return []

    @abstractmethod
    def get_item(self, id):
        return None

    @abstractmethod
    def get_identifier_string(self):
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

    def get_id(self):
        result = hashlib.md5(self.get_identifier_string().encode())
        return result.hexdigest()

    def get_representation(self):
        # items = self.get_items()
        response = {
            'name': self.get_name(),
            'id': self.get_id()
        }
        # if items:
        #    response['items'] = [i.get_representation() for i in items]
        props = self.get_properties()
        if props:
            response['properties'] = props
        return response

    def get_items_representation(self):
        items = self.get_items()

        if items:
            return [i.get_representation() for i in items]
        else:
            return []
