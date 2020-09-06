from .folder_item import FolderItem

class Items:

    def __init__(self):
        self.items = [FolderItem("f1", "/Users/marko/playground")]

    def get_items(self):
        return self.items

    @classmethod
    def load(cls):
        return Items()
