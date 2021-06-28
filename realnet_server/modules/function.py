from .module import Module


class Function(Module):
    def get_item(self, item):
        pass

    def get_items(self, item):
        pass

    def delete_item(self, item):
        pass

    def update_item(self, item, **kwargs):
        pass

    def create_item(self, parent_item=None, **kwargs):
        pass

    def get_item_data(self, item):
        pass

    def update_item_data(self, item, storage):
        pass

    def delete_item_data(self, item):
        pass