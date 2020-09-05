from pynecone import Shell
from .start import Start


class Server(Shell):

    def get_commands(self):
        return [Start()]