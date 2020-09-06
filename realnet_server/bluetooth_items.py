from .item import Item
from .bluetooth_item import BluetoothItem

# import bluetooth


class BluetoothItems(Item):

    def get_items(self):
        return []
        items = []
        for device in bluetooth.discover_devices(lookup_names=True):
            items.append(BluetoothItem(device))
        return items

    def get_item(self, id):
        return None
        for device in bluetooth.discover_devices(lookup_names=True):
            item = BluetoothItem(device)
            if id == item.get_id():
                return item
        return None

    def get_identifier_string(self):
        return 'devices'

    def get_name(self):
        return 'Devices'

    def get_properties(self):
        return None

    def get_data(self):
        return None