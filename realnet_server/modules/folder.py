from .module import Module
from realnet_server.models import Item
from flask import jsonify

class Folder(Module):

    def get_items(self, item):
        return jsonify([i.to_dict() for i in Item.query.filter(Item.parent_id == item.id)])

    def get_item(self, item):
        retrieved_item = Item.query.filter(Item.id == item.id).first()
        if retrieved_item:
            return jsonify({'id': retrieved_item.id})

        return None