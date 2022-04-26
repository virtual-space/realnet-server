from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from flask import request, jsonify, send_file, Response
from .models import db, Item, Type, Account, AccountGroup, Acl, AclType, Function, Topic, Message, TopicFunction, VisibilityType
from .auth import require_oauth
import importlib
import json
import uuid
import base64


from sqlalchemy.sql import func, and_, or_, not_, functions
try:
    from urllib.parse import unquote  # PY3
except ImportError:
    from urllib import unquote  # PY2

def load_module(module_name):  
    target_name = 'default'
    if module_name:
        target_name = module_name   
    module = importlib.import_module('realnet_server.modules.{}'.format(target_name))
    module_class = getattr(module, target_name.capitalize())
    return module_class()

def get_module_by_id(id):
    module_name = 'default'

    if id:
        ids = id.split("_")
        if len(ids) > 1:
            parent_id = ids[0]
            parent_item = Item.query.filter(Item.id == parent_id).first()
            if parent_item and parent_item.type.module:
                module_name = parent_item.type.module
        
    return load_module(module_name)

def get_item_module_by_id(id):
    module_name = 'default'
    item_id = id
    ids = id.split("_")
    if len(ids) > 1:
        item_id = ids[0]
        
    if item_id:
        item = Item.query.filter(Item.id == item_id).first()
        if item and item.type.module:
            module_name = item.type.module
            
    return load_module(module_name)

def get_module_by_name(name):
    module_name = 'default'

    if name:
        type = Type.query.filter(Type.name == name).first()
        if type:
            module_name = type.module
        
    return load_module(module_name)

def get_module():
    return load_module('default')

def extract_search_data(request):
    
        data = dict()
            
        home = request.args.get('home')
        if home:
            data['home'] = home

        parent_id = request.args.get('parent_id')
        if parent_id:
            data['parent_id'] = parent_id

        my_items = request.args.get('my_items')
        if my_items:
            data['my_items'] = my_items

        name = request.args.get('name')
        if name:
            data['name'] = name

        type_names = request.args.getlist('types')

        if type_names:
            data['type_names'] = type_names

        keys = request.args.getlist('key')

        if keys:
            data['keys'] = keys

        values = request.args.getlist('value')

        if values:
            data['values'] = values

        lat = request.args.get('lat')

        if lat:
            data['lat'] = lat

        lng = request.args.get('lng')

        if lng:
            data['lng'] = lng
        
        radius = request.args.get('radius', 100.00)

        if radius:
            data['radius'] = radius

        visibility = request.args.get('visibility')

        if visibility:
            data['visibility'] = visibility

        tags = request.args.getlist('tags')

        if tags:
            data['tags'] = tags

        return data


def perform_search(request, account, module, public=False):
    data = extract_search_data(request)
    
    if public:
        return jsonify([i.to_dict() for i in module.perform_search(None, account, data, public) if module.is_item_public(i)]), 200
    else:
        return jsonify([i.to_dict() for i in module.perform_search(None, account, data, public) if module.can_account_read_item(account, i)]), 200



@app.route('/public/items', methods=['GET'])
def public_items():
    return perform_search(request, None, get_module(), True)



@app.route('/public/items/<id>', methods=['GET'])
def public_single_item(id):
    module = get_module_by_id(id)
    if module:
        item = module.get_item(id)
        if item:
            if not module.is_item_public(item=item):
                return jsonify(isError=True,
                           message="Failure",
                           statusCode=403,
                           data='Account not authorized to read this item'), 403

            return jsonify(item.to_dict()), 200
        else:
            return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404



@app.route('/public/items/<id>/data', methods=['GET'])
def single_item_data(id):
    module = get_module_by_id(id)
    if module:
        item = module.get_item(id)
        if item:
            if not module.is_item_public(item=item):
                return jsonify(isError=True,
                           message="Failure",
                           statusCode=403,
                           data='Account not authorized to read this item'), 403

            output = module.get_item_data(item)

            if 's3_obj' in output:
                print('*** returning s3_obj {}'.format(output))
                read = output['s3_obj']['Body'].read()
                return Response(
                    base64.b64encode(read).decode('utf-8'),
                    mimetype=output['mimetype'],
                    headers={"Content-Disposition": "attachment;filename={}".format(output['filename'])}
                )
            elif 'filename' in output:
                print('*** returning local file')
                return send_file(output['filename'], as_attachment=True)
            else:
                return jsonify(isError=True,
                            message="Failure",
                            statusCode=500,
                            data='get item {0} data'.format(id)), 500
        else:
            return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404


@app.route('/items', methods=['GET', 'POST'])
@require_oauth()
def items():
    if request.method == 'POST':
        request.on_json_loading_failed = lambda x: print('json parsing error: ', x)
        input_data = request.get_json(force=True, silent=False)
        if input_data:
            input_type = Type.query.filter(Type.name == input_data['type']).first()
            if input_type:
                module_instance = load_module(input_type.module)

                input_name = input_data['name']
                if input_name:
                    parent_id = None

                    if 'home' in input_data:
                        folder = Item.query.filter(Item.parent_id == current_token.account.id, Item.name == 'Home').first()
                        if folder:
                            parent_id = folder.id

                    if not parent_id and 'parent_id' in input_data:
                        parent_id = input_data['parent_id']
                        ids = parent_id.split("_")
                        if len(ids) > 1:
                            parent_id = ids[0]
                        parent = Item.query.filter(Item.id == parent_id).first()
                        if not parent:
                            return jsonify(isError=True,
                                           message="Failure",
                                           statusCode=404,
                                           data='Parent item not found'), 404

                        account = Account.query.filter(Account.id == current_token.account.id).first()

                        if not module_instance.can_account_write_item(account=account,item=parent):
                            return jsonify(isError=True,
                                           message="Failure",
                                           statusCode=403,
                                           data='Account not authorized to write to parent'), 403
                    if not parent_id:
                        parent_id = current_token.account.home_id

                    input_attributes = None

                    if 'attributes' in input_data:
                        input_attributes = input_data['attributes']

                    input_location = None

                    if 'location' in input_data:
                        input_location = input_data['location']

                    input_visibility = None

                    if 'visibility' in input_data:
                        input_visibility = input_data['visibility']
                    else:
                        input_visibility = 'restricted'

                    input_tags = None

                    if 'tags' in input_data:
                        input_tags = input_data['tags']

                    parent_item = None

                    if parent_id:
                        parent_item = Item.query.filter(Item.id == parent_id).first()

                    args = dict()

                    if input_name:
                        args['name'] = input_name

                    if input_attributes:
                        args['attributes'] = input_attributes

                    if input_location:
                        args['location'] = input_location

                    if input_visibility:
                        args['visibility'] = input_visibility

                    if input_tags:
                        args['tags'] = input_tags

                    args['owner_id'] = current_token.account.id
                    args['group_id'] = current_token.account.group_id
                    args['type_id'] = input_type.id
                    args['parent_id'] = input_data['parent_id']

                    created_item = module_instance.create_item(parent_item=parent_item, **args)

                    if 'public' in input_data:
                        acl = Acl(id=str(uuid.uuid4()), type=AclType.public, name='public', permission='r',
                                  item_id=created_item.id)
                        db.session.add(acl)
                        db.session.commit()

                    return jsonify(created_item.to_dict()), 201
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
        data = extract_search_data(request)
        type_names = request.args.getlist('types')
        public = request.args.getlist('public')
        account = current_token.account
        results = []
        parent_id = request.args.get('parent_id')
        parent_module = get_module()
        if parent_id:
            parent_module = get_item_module_by_id(parent_id)
        
        if type_names:
            types = Type.query.filter(Type.name.in_(type_names)).all()
            for extended_type in  [t for t in types if t.module]:
                module_instance = load_module(extended_type.module)
                results.extend(module_instance.perform_search(parent_id, account, data, public))
            if [t for t in types if not t.module]: 
                results.extend(parent_module.perform_search(parent_id, account, data, public))
        else:  
            results.extend(parent_module.perform_search(parent_id, account, data, public))

        if public:
            return jsonify([i.to_dict() for i in results if parent_module.is_item_public(i)]), 200
        else:
            return jsonify([i.to_dict() for i in results if parent_module.can_account_read_item(account, i)]), 200



@app.route('/items/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_item(id):
    module_instance = get_module_by_id(id)
    item = module_instance.get_item(id)
    if item:
        if request.method == 'PUT':

            if not module_instance.can_account_write_item(account=current_token.account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to write to item'), 403

            input_data = request.get_json(force=True, silent=False)

            args = dict()

            if 'name' in input_data:
                args['name'] = input_data['name']

            if 'parent_id' in input_data:
                args['parent_id'] = input_data['parent_id']

                parent = Item.query.filter(Item.id == args['parent_id']).first()

                if not parent:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=404,
                                   data='Parent item not found'), 404

                if not module_instance.can_account_write_item(account=current_token.account, item=parent):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to parent'), 403


            if 'attributes' in input_data:
                args['attributes'] = input_data['attributes']

            if 'location' in input_data:
                args['location'] = input_data['location']

            if 'visibility' in input_data:
                args['visibility'] = input_data['visibility']
            elif 'public' in input_data:
                args['visibility'] = 'visible' if input_data['public'] else 'restricted'

            if 'tags' in input_data:
                args['tags'] = input_data['tags']

            module_instance.update_item(item, **args)

            return jsonify(item.to_dict())

        elif request.method == 'DELETE':

            if not module_instance.can_account_delete_item(account=current_token.account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to delete this item'), 403

            module_instance.delete_item(item)
            return jsonify(isError=False,
                           message="Success",
                           statusCode=200,
                           data='deleted item {0}'.format(id)), 200
        else:
            if not module_instance.can_account_read_item(account=current_token.account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this item'), 403
            retrieved_item = module_instance.get_item(id)
            if retrieved_item:
                return jsonify(retrieved_item.to_dict()), 200
            else:
                return jsonify(isError=True,
                            message="Failure",
                            statusCode=500,
                            data='get_item {0}'.format(id)), 500

    return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='get_item {0}'.format(id)), 404




@app.route('/items/<id>/data', methods=['GET', 'PUT', 'POST', 'DELETE'])
@require_oauth()
def item_data(id):
    module_instance = get_module_by_id(id)
    item = module_instance.get_item(id)
    if item:
        if request.method == 'PUT' or request.method == 'POST':

            if 'file' not in request.files:
                return jsonify(isError=True,
                           message="Failure",
                           statusCode=400,
                           data='Bad request: file missing from the request'), 400

            file = request.files['file']
            # If the user does not select a file, the browser submits an
            # empty file without a filename.
            if file.filename == '':
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=400,
                               data='Bad request: file content missing from the request'), 400

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not module_instance.can_account_write_item(account=account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to write data into this item'), 403

            if file and module_instance.allowed_file(file.filename):
                print('request data')
                print('request', request)
                print('files', request.files)
                print('file', file)
                print('item', item)
                result = module_instance.update_item_data(item, file)
                if result['created'] or result['updated']:
                    code = 201
                    if result['updated']:
                        code = 200
                    return jsonify({'url': '/items/{}/data'.format(item.id)}), code
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=500,
                                   data='Internal server error'), 500
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=400,
                               data='Unsupported file type'), 400

        elif request.method == 'DELETE':

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not module_instance.can_account_write_item(account=account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to delete data from this item'), 403

            if module_instance.delete_item_data(item):
                return jsonify(isError=False,
                               message="Success",
                               statusCode=200,
                               data='deleted item {0}'.format(id)), 200
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=500,
                               data='Internal server error'), 500
        else:
            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not module_instance.can_account_read_item(account=account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read data from this item'), 403

            output = module_instance.get_item_data(item)

        if 's3_obj' in output:
            return Response(
                output['s3_obj']['Body'].read(),
                mimetype=output['mimetype'],
                headers={"Content-Disposition": "attachment;filename={}".format(output['filename'])}
            )
        elif 'filename' in output:
            return send_file(output['filename'], as_attachment=True)
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=500,
                           data='get_item {0}'.format(id)), 500

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404


@app.route('/items/<id>/invoke', methods=['POST'])
@require_oauth()
def item_invoke(id):
    module = get_module_by_id(id)
    if module:
        item = module.get_item(id)
        if item:
            if not module.can_account_execute_item(account=current_token.account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to execute this item'), 403

            arguments = request.get_json(force=True, silent=False)
            return jsonify(module.invoke(item, arguments)), 200
        else:
            return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404


@app.route('/items/<id>/message', methods=['POST'])
@require_oauth()
def item_message(id):
    module = get_module_by_id(id)
    if module:
        item = module.get_item(id)
        if item:
            if not module.can_account_message_item(account=current_token.account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to message this item'), 403

            arguments = request.get_json(force=True, silent=False)
            return jsonify(module.message(item, arguments)), 200
        else:
            return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404


@app.route('/items/<id>/import', methods=['POST'])
@require_oauth()
def item_import(id):
    module = get_module_by_id(id)
    if module:
        item = module.get_item(id)
        if item:

            if 'file' not in request.files:
                return jsonify(isError=True,
                           message="Failure",
                           statusCode=400,
                           data='Bad request: file missing from the request'), 400

            file = request.files['file']
            # If the user does not select a file, the browser submits an
            # empty file without a filename.
            if file.filename == '':
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=400,
                               data='Bad request: file content missing from the request'), 400

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not module.can_account_write_item(account=account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to write data into this item'), 403

            if file and module.allowed_file(file.filename):
                print('request data')
                print('request', request)
                print('files', request.files)
                print('file', file)
                print('item', item)
                result = module.import_file(item, file)
                if result['created'] or result['updated']:
                    code = 201
                    if result['updated']:
                        code = 200
                    return jsonify({'url': '/items/{}'.format(item.id)}), code
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=500,
                                   data='Internal server error'), 500
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=400,
                               data='Unsupported file type'), 400
        else:
            return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404


@app.route('/items/<id>/acls', methods=['GET', 'POST'])
@require_oauth()
def item_acls(id):
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:
        if item.owner_id == current_token.account.id or item.group_id == current_token.account.group_id:
            if request.method == 'POST':
                input_data = request.get_json(force=True, silent=False)

                type = None
                name = None
                permission = None

                if 'name' in input_data:
                    name = input_data['name']

                if 'type' in input_data:
                    type = input_data['type']

                if 'permission' in input_data:
                    permission = input_data['permission']

                if type == None or name == None or permission == None:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=400,
                                   data='Bad request, name, type or permission missing'), 400

                acl = Acl(id=str(uuid.uuid4()), type=AclType[type], name=name, permission=permission, item_id=item.id)
                db.session.add(acl)
                db.session.commit()
                return jsonify(acl.to_dict()), 201
            else:
                return jsonify([a.to_dict() for a in Acl.query.filter(Acl.item_id == item.id)])
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=403,
                           data='Account not authorized to read/modify acls from this item'), 403
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404


@app.route('/items/<id>/acls/<aclid>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def item_acl(id, aclid):
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:
        if item.owner_id == current_token.account.id or item.group_id == current_token.account.group_id:
            acl = Acl.query.filter(Acl.id == aclid and Acl.item_id == id).first()
            if acl:
                if request.method == 'GET':
                    return jsonify(acl.to_dict()), 200
                elif request.method == 'DELETE':
                    db.session.delete(acl)
                    db.session.commit()
                    return jsonify(isError=False,
                                   message="Success",
                                   statusCode=200,
                                   data='deleted acl {0}'.format(aclid)), 200
                elif request.method == 'PUT':
                    input_data = request.get_json(force=True, silent=False)

                    if 'name' in input_data:
                        acl.name = input_data['name']

                    if 'type' in input_data:
                        acl.type = AclType[input_data['type']]

                    if 'permission' in input_data:
                        acl.permission = input_data['permission']

                    db.session.commit()

                    return jsonify(acl.to_dict()), 200
                else:
                    jsonify([a.to_dict() for a in Acl.query.filter(Acl.item_id == item.id)])
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='ACl {0} not found'.format(aclid)), 404
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=403,
                           data='Account not authorized to read/modify acls from this item'), 403
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404



