import json

from pynecone import Command
from flask import Flask

from .items import Items
from .folder_item import FolderItem


class Start(Command):

    def __init__(self):
        super().__init__("start")
        self.items = Items.load()
        self.item = FolderItem("playground", "/Users/marko/playground")

    def run(self, args):

        app = Flask('realnet-server')

        @app.route('/')
        def root():
            return json.dumps(self.item.get_representation())

        @app.route('/items')
        def items():
            return json.dumps(self.item.get_items_representation())

        @app.route('/items/<identifier>')
        def item(identifier):
            return json.dumps(self.item.get_item(identifier).get_representation())

        @app.route('/items/<identifier>/items')
        def children(identifier):
            return json.dumps(self.item.get_item(identifier).get_items_representation())

        app.run('localhost', port=5000)