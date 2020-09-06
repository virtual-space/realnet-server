from .item import Item


class FileItem(Item):

    def __init__(self, name, path):
        self.name = name
        self.path = path

    def get_items(self):
        return None

    def get_item(self):
        return None

    def get_name(self):
        return self.name

    def get_properties(self):
        pass

    def get_data(self):
        pass

    def get_identifier_string(self):
        return self.path
