from .module import Module
from realnet_server.models import Account
from flask import jsonify

class Person(Module):
    def create_item(self, parent_item=None, **kwargs):
        pass

    def get_item_data(self, item):
        pass

    def update_item_data(self, item, storage):
        pass

    def delete_item_data(self, item):
        pass

    def get_items(self, item):
        pass

    def delete_item(self, item):
        pass

    def update_item(self, item, **kwargs):
        pass

    def get_item(self, item):
        account = Account.query.filter(Account.id == item.id).first()
        if account:
            return jsonify({'id': account.id, 'name': account.username})

        return None

