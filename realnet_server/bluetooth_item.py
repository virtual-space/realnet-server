from .item import Item


class BluetoothItem(Item):

    def __init__(self, device):
        self.device = device

    def get_items(self):
        return None

    def get_item(self, id):
        return None

    def get_identifier_string(self):
        return self.device

    def get_name(self):
        return self.device

    def get_properties(self):
        return None

    def get_data(self):
        return None