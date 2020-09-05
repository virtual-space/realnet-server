from pynecone import Command


class Start(Command):

    def __init__(self):
        super().__init__("start")

    def run(self, args):
        print("started")