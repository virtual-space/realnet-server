import json

from pynecone import Command
from flask import Flask

from .items import Items
from .folder_item import FolderItem


class Start(Command):

    def __init__(self):
        super().__init__("start")
        self.items = Items.load()
        self.item = FolderItem("f1", "/Users/marko/playground")

    def run(self, args):

        app = Flask('realnet-server')

        @app.route('/')
        def items():
            return json.dumps(self.item.get_representation())

        app.run('localhost', port=5000)