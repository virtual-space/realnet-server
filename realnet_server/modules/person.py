from .module import Module
from realnet_server.models import Account
from flask import jsonify

class Person(Module):
    def get_item(self, item):
        account = Account.query.filter(Account.id == item.id).first()
        if account:
            return jsonify({'id': account.id})

        return None

