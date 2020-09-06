from .item import Item
import psutil


class ProcessItem(Item):

    def __init__(self, proc):
        self.proc = proc
        try:
            self.name = self.proc.name()
            self.pid = self.proc.pid
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    def get_items(self):
        return None

    def get_item(self, id):
        return None

    def get_identifier_string(self):
        return str(self.pid)

    def get_name(self):
        return self.name

    def get_properties(self):
        return self.proc.as_dict()

    def get_data(self):
        return None
