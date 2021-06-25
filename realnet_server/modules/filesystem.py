from .module import Module
import os

from flask import jsonify


class Filesystem(Module):

    def get_items(self, item):
        items = []
        if os.path.isdir(item.attributes['path']):
            for f in os.listdir(item.attributes['path']):
                items.append({'id': os.path.join(item.attributes['path'], f)})
        return jsonify(items)

    def get_item(self, item):
        pass

