from pynecone import Shell
from .api import Api


class RealnetServer(Shell):

    def __init__(self):
        super().__init__('realnet-server')

    def get_commands(self):
        return [Api()]

    def add_arguments(self, parser):
        pass

    def get_help(self):
        return 'realnet server'