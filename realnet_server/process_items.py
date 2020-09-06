from .item import Item
from .process_item import ProcessItem
import psutil

class ProcessItems(Item):

    def get_items(self):
        items = []
        for proc in psutil.process_iter():
            items.append(ProcessItem(proc))
        return items

    def get_item(self, id):
        for proc in psutil.process_iter():
            item = ProcessItem(proc)
            if id == item.get_id():
                return item
        return None

    def get_identifier_string(self):
        return 'processes'

    def get_name(self):
        return 'Processes'

    def get_properties(self):
        return None

    def get_data(self):
        return None