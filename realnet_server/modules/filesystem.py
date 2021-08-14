from .module import Module
import os

from flask import jsonify


class Filesystem(Module):

    def create_item(self, parent_item=None, **kwargs):
        pass

    def get_item_data(self, item):
        pass

    def update_item_data(self, item, storage):
        pass

    def delete_item_data(self, item):
        pass

    def delete_item(self, item):
        pass

    def update_item(self, item, **kwargs):
        pass

    def get_items(self, item):
        items = []
        if os.path.isdir(item['attributes']['path']):
            for f in os.listdir(item['attributes']['path']):
                items.append({'id': os.path.join(item['attributes']['path'], f)})
        return jsonify(items)

    def get_item(self, item):
        return item

