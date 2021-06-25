from realnet_server import app
from flask import request, jsonify
from .models import db, Type, Item
import importlib

@app.route('/items', methods=['GET'])
def get_items():
    return jsonify([i.to_dict() for i in Item.query.filter(Item.parent_id == None)]), 200


@app.route('/items', methods=['POST'])
def create_item():
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data=request.json), 200


@app.route('/items/<id>', methods=['GET'])
def get_item(id):
    # 1. get the type
    item = Item.query.filter(Item.id == id).first()
    if item:
        # 2. see if type has a module
        if item.type.module:
            module = importlib.import_module('realnet_server.modules.{}'.format(item.type.module))
            module_class = getattr(module, item.type.module.capitalize())
            module_instance = module_class()
            retrieved_item = module_instance.get_item(item)
            if retrieved_item:
                return retrieved_item
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=500,
                               data='get_item {0}'.format(id)), 500
        else:
            return jsonify(item.to_dict())

    return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='get_item {0}'.format(id)), 404


@app.route('/items/<id>', methods=['PUT'])
def put_item(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='put_item {0}'.format(id)), 200


@app.route('/items/<id>', methods=['DELETE'])
def delete_item(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='delete_item {0}'.format(id)), 200


@app.route('/items/<id>/data', methods=['GET', 'PUT', 'DELETE'])
def handle_item(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='handle_item_data {0}'.format(id)), 200

@app.route('/items/<id>/items', methods=['GET', 'POST'])
def item_items(id):
    # 1. get the type
    item = Item.query.filter(Item.id == id).first()
    if item:
        # 2. see if type has a module
        if item.type.module:
            module = importlib.import_module('realnet_server.modules.{}'.format(item.type.module))
            module_class = getattr(module, item.type.module.capitalize())
            module_instance = module_class()
            retrieved_items = module_instance.get_items(item)
            return retrieved_items
        else:
            return jsonify([])

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404



