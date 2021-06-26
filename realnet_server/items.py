from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from flask import request, jsonify
from .models import db, Item, Type
from .auth import require_oauth
import importlib
import uuid


@app.route('/items', methods=['GET', 'POST'])
@require_oauth()
def items():
    if request.method == 'POST':
        request.on_json_loading_failed = lambda x: print('json parsing error: ',x)
        input_data = request.get_json(force=True,silent=False)
        if input_data:
            input_type = Type.query.filter(Type.name == input_data['type'].capitalize()).first()
            if input_type:
                input_name = input_data['name']
                if input_name:
                    # print(current_token.account.group_id)
                    parent_id = None

                    if 'parent_id' in input_data:
                        parent_id = input_data['parent_id']

                    if not parent_id:
                        parent_id = current_token.account.home_id

                    attributes = None

                    if 'attributes' in input_data:
                        attributes = input_data['attributes']

                    item = Item(id=str(uuid.uuid4()),
                                        name=input_name,
                                        owner_id=current_token.account.id,
                                        group_id=current_token.account.group_id,
                                        type_id=input_type.id,
                                        parent_id=parent_id,
                                        attributes=attributes)
                    db.session.add(item)
                    db.session.commit()
                    return jsonify(item.to_dict()), 201
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=400,
                                   data='Missing parameter: name'), 400
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=400,
                               data='Missing parameter: type'), 400
        else:
            return jsonify(isError=True,
                               message="Failure",
                               statusCode=400,
                               data='Bad request'), 400
    else:
        return jsonify([i.to_dict() for i in Item.query.filter(Item.parent_id == None)]), 200


@app.route('/items/<id>', methods=['GET', 'PUT', 'DELETE'])
def single_item(id):
    # 1. get the type
    item = Item.query.filter(Item.id == id).first()
    if item:
        module_name = item.type.module

        if not module_name:
            module_name = 'default'

        module = importlib.import_module('realnet_server.modules.{}'.format(module_name))
        module_class = getattr(module, item.type.module.capitalize())
        module_instance = module_class()

        if request.method == 'PUT':
            input_data = request.get_json(force=True, silent=False)

            args = dict()

            if 'name' in input_data:
                args['name'] = input_data['name']

            if 'parent_id' in input_data:
                args['parent_id'] = input_data['parent_id']

            if 'attributes' in input_data:
                args['attributes'] = input_data['attributes']

            module_instance.update_item(item, **args)

            return jsonify(item.to_dict())

        elif request.method == 'DELETE':
            module_instance.delete_item(item)
            return jsonify(isError=False,
                           message="Success",
                           statusCode=200,
                           data='deleted item {0}'.format(id)), 200
        else:
            retrieved_item = module_instance.get_item(item)

        if retrieved_item:
            return retrieved_item
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=500,
                           data='get_item {0}'.format(id)), 500

    return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='get_item {0}'.format(id)), 404


@app.route('/items/<id>/data', methods=['GET', 'PUT', 'DELETE'])
def item_data(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='handle_item_data {0}'.format(id)), 200


@app.route('/items/<id>/acls', methods=['GET', 'POST'])
def item_acls(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='handle_item_data {0}'.format(id)), 200


@app.route('/items/<id>/acls/<aclid>', methods=['GET', 'PUT', 'DELETE'])
def item_acl(id, aclid):
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



