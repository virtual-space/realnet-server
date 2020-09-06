from .item import Item
from .file_item import FileItem
import os


class FolderItem(Item):

    def __init__(self, name, path):
        self.name = name
        self.path = path

    def get_items(self):
        items = []
        for filename in os.listdir(self.path):
            full_path = os.path.join(self.path, filename)
            if os.path.isdir(os.path.join(self.path, filename)):
                items.append(FolderItem(filename, full_path))
            else:
                items.append(FileItem(filename, full_path))
        return items

    def get_name(self):
        return self.name

    def get_id(self):
        return self.path

    def get_properties(self):
        pass

    def get_data(self):
        pass

