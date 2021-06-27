from .module import Module
from realnet_server.models import db, Item
from flask import jsonify


class Default(Module):

    def create_item(self, parent_item=None, **kwargs):
        pass

    def get_item_data(self, item):
        pass

    def update_item_data(self, item, filename):
        pass

    def delete_item_data(self, item, filename):
        pass

    def delete_item(self, item):
        db.session.delete(item)
        db.session.commit()

    def update_item(self, item, **kwargs):
        print(kwargs.items())
        for key, value in kwargs.items():
            print("%s == %s" % (key, value))
            if key == 'name':
                item.name = value
            elif key == 'parent_id':
                item.parent_id = value
            elif key == 'attributes':
                item.attributes = value

        db.session.commit()

    def get_items(self, item):
        return jsonify([i.to_dict() for i in Item.query.filter(Item.parent_id == item.id)])

    def get_item(self, item):
        retrieved_item = Item.query.filter(Item.id == item.id).first()
        if retrieved_item:
            return jsonify({'id': retrieved_item.id,
                            'name': retrieved_item.name,
                            'attributes': retrieved_item.attributes,
                            'type': retrieved_item.type.to_dict(),
                            'parent_id': retrieved_item.parent_id})

        return None
