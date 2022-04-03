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


def can_account_execute_item(account, item):
    if [acl for acl in item.acls if acl.type == AclType.public]:
        return True

    if [acl for acl in item.acls if acl.type == AclType.user and acl.name == account.username and 'e' in acl.permission]:
        return True

    account_groups = set([ag.name for ag in AccountGroup.query.filter(AccountGroup.account_id == account.id)])

    if [acl for acl in item.acls if acl.type == AclType.group and acl.name in account_groups and 'e' in acl.permission]:
        return True

    account_group = AccountGroup.query.filter(AccountGroup.group_id == item.group_id, AccountGroup.account_id == account.id).first()

    if account_group:
        return True

    if item.owner_id == account.id:
        return True


def can_account_message_item(account, item):
    if [acl for acl in item.acls if acl.type == AclType.public]:
        return True

    if [acl for acl in item.acls if acl.type == AclType.user and acl.name == account.username and 'm' in acl.permission]:
        return True

    account_groups = set([ag.name for ag in AccountGroup.query.filter(AccountGroup.account_id == account.id)])

    if [acl for acl in item.acls if acl.type == AclType.group and acl.name in account_groups and 'm' in acl.permission]:
        return True

    account_group = AccountGroup.query.filter(AccountGroup.group_id == item.group_id, AccountGroup.account_id == account.id).first()

    if account_group:
        return True

    if item.owner_id == account.id:
        return True


def can_account_read_item(account, item):
    if [acl for acl in item.acls if acl.type == AclType.public]:
        return True

    if [acl for acl in item.acls if acl.type == AclType.user and acl.name == account.username and ('r' in acl.permission or 'w' in acl.permission)]:
        return True

    ags = AccountGroup.query.filter(AccountGroup.account_id == account.id).all()
    account_groups = set([ag.group.name for ag in ags])

    if [acl for acl in item.acls if acl.type == AclType.group and acl.name in account_groups and ('r' in acl.permission or 'w' in acl.permission)]:
        return True

    account_group = AccountGroup.query.filter(AccountGroup.group_id == item.group_id, AccountGroup.account_id == account.id).first()

    if account_group:
        return True

    if item.owner_id == account.id:
        return True

def is_item_public(item):

    if [acl for acl in item.acls if acl.type == AclType.public]:
        return True

    return False


def can_account_write_item(account, item):
    if [acl for acl in item.acls if
        acl.type == AclType.user and acl.name == account.username and 'w' in acl.permission]:
        return True

    account_groups = set([ag.group.name for ag in AccountGroup.query.filter(AccountGroup.account_id == account.id)])

    if [acl for acl in item.acls if
        acl.type == AclType.group and acl.name in account_groups and 'w' in acl.permission]:
        return True

    account_group = AccountGroup.query.filter(AccountGroup.group_id == item.group_id, AccountGroup.account_id == account.id).first()

    if account_group:
        return True

    if item.owner_id == account.id:
        return True


def can_account_delete_item(account, item):
    account_group = AccountGroup.query.filter(
        AccountGroup.group_id == item.group_id, AccountGroup.account_id == account.id).first()
    if account_group:
        return True
    return item.owner_id == account.id


def filter_readable_items(account, items_json):
    return [i for i in json.loads(items_json) if can_account_read_item(account, Item(**i))] if items_json else []


def perform_search(request, account, public=False):
    conditions = []

    parent_id = request.args.get('parent_id')

    my_items = request.args.get('my_items')

    if parent_id:
        conditions.append(Item.parent_id == parent_id)
    elif my_items and account:
        conditions.append(Item.owner_id == account.id)
    else:
        root_item_name = app.config.get('ROOT_ITEM')
        if root_item_name:
            root_item = Item.query.filter(Item.name == root_item_name).first()
            if root_item:
                conditions.append(Item.parent_id == root_item.id)
            else:
                conditions.append(Item.parent_id == None)

    name = request.args.get('name')

    if name:
        conditions.append(Item.name.ilike('{}%'.format(unquote(name))))

    type_names = request.args.getlist('types')

    if type_names:
        print(type_names)
        type_ids = [ti.id for ti in Type.query.filter(Type.name.in_(type_names)).all()]
        derived_type_ids = [ti.id for ti in Type.query.filter(Type.base_id.in_(type_ids)).all()]
        conditions.append(Item.type_id.in_(list(set(type_ids + derived_type_ids))))

    keys = request.args.getlist('key')

    values = request.args.getlist('value')

    for kv in zip(keys, values):
        conditions.append(Item.attributes[kv[0]].astext == kv[1])

    lat = request.args.get('lat')
    lng = request.args.get('lng')
    radius = request.args.get('radius', 100.00)

    if lat and lng:
        range = (0.00001) * float(radius)
        conditions.append(func.ST_DWithin(Item.location, 'SRID=4326;POINT({} {})'.format(lng, lat), range))

    visibility = request.args.get('visibility')

    if visibility:
        conditions.append(Item.visibility == VisibilityType[visibility])

    tags = request.args.getlist('tags')

    if tags:
        conditions.append(Item.tags.contains(tags))

    if public:
        if not conditions:
            return jsonify([])
        else:
            return jsonify([i.to_dict() for i in Item.query.filter(*conditions) if is_item_public(i)]), 200
    else:
        if not conditions:
            conditions.append(Item.parent_id == current_token.account.home_id)
        return jsonify([i.to_dict() for i in Item.query.filter(*conditions) if can_account_read_item(account, i)]), 200



@app.route('/public/items', methods=['GET'])
def public_items():
    return perform_search(request, None, True)

@app.route('/public/items/<id>', methods=['GET'])
def public_single_item(id):
    item = Item.query.filter(Item.id == id).first()
    if item:
        module_name = item.type.module

        if not module_name:
            module_name = 'default'

        module = importlib.import_module('realnet_server.modules.{}'.format(module_name))
        module_class = getattr(module, module_name.capitalize())
        module_instance = module_class()

        if not is_item_public(item=item):
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=403,
                           data='Account not authorized to read this item'), 403

        retrieved_item = module_instance.get_item(item)

        return retrieved_item
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Item {0} not found'.format(id)), 404


@app.route('/public/items/<id>/data', methods=['GET'])
def single_item_data(id):
    item = Item.query.filter(Item.id == id).first()
    if item:
        if not is_item_public(item=item):
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=403,
                           data='Account not authorized to read this item'), 403

        module_name = item.type.module

        if not module_name:
            module_name = 'default'

        module = importlib.import_module('realnet_server.modules.{}'.format(module_name))
        module_class = getattr(module, module_name.capitalize())
        module_instance = module_class()

        output = module_instance.get_item_data(item)

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

@app.route('/items', methods=['GET', 'POST'])
@require_oauth()
def items():
    if request.method == 'POST':
        request.on_json_loading_failed = lambda x: print('json parsing error: ', x)
        input_data = request.get_json(force=True, silent=False)
        if input_data:
            input_type = Type.query.filter(Type.name == input_data['type'].capitalize()).first()
            if input_type:

                module_name = input_type.module

                if not module_name:
                    module_name = 'default'

                module = importlib.import_module('realnet_server.modules.{}'.format(module_name))
                module_class = getattr(module, module_name.capitalize())
                module_instance = module_class()

                input_name = input_data['name']
                if input_name:
                    parent_id = None

                    if 'parent_id' in input_data:
                        parent_id = input_data['parent_id']

                        parent = Item.query.filter(Item.id == parent_id).first()
                        if not parent:
                            return jsonify(isError=True,
                                           message="Failure",
                                           statusCode=404,
                                           data='Parent item not found'), 404

                        account = Account.query.filter(Account.id == current_token.account.id).first()

                        if not can_account_write_item(account=account,item=parent):
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

                    created_item = module_instance.create_item(parent_item=parent_item, **args)

                    if 'public' in input_data:
                        i = json.loads(created_item)
                        acl = Acl(id=str(uuid.uuid4()), type=AclType.public, name='public', permission='r',
                                  item_id=i['id'])
                        db.session.add(acl)
                        db.session.commit()
                        pass

                    return created_item, 201
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
        return perform_search(request, current_token.account, False)


@app.route('/items/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_item(id):
    # 1. get the type
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:
        module_name = item.type.module

        if not module_name:
            module_name = 'default'

        module = importlib.import_module('realnet_server.modules.{}'.format(module_name))
        module_class = getattr(module, module_name.capitalize())
        module_instance = module_class()

        if request.method == 'PUT':

            if not can_account_write_item(account=current_token.account, item=item):
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

                if not can_account_write_item(account=current_token.account, item=parent):
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

            if not can_account_delete_item(account=current_token.account, item=item):
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
            if not can_account_read_item(account=current_token.account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this item'), 403
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


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'md'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/items/<id>/data', methods=['GET', 'PUT', 'POST', 'DELETE'])
@require_oauth()
def item_data(id):
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:
        module_name = item.type.module

        if not module_name:
            module_name = 'default'

        module = importlib.import_module('realnet_server.modules.{}'.format(module_name))
        module_class = getattr(module, module_name.capitalize())
        module_instance = module_class()

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

            if not can_account_write_item(account=account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to write data into this item'), 403

            if file and allowed_file(file.filename):
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

            if not can_account_write_item(account=account, item=item):
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

            if not can_account_read_item(account=account, item=item):
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


@app.route('/items/<id>/functions', methods=['GET', 'POST'])
@require_oauth()
def item_functions(id):
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:

        if request.method == 'POST':
            input_json = request.get_json(force=True, silent=False)

            input_name = input_json['name']
            if input_name:

                if not can_account_write_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to item'), 403

                func = Function.query.filter(Function.item_id == item.id and Function.name == input_name).first()

                if func:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=400,
                                   data='A function with the same name already exists'), 400

                input_code = input_json['code']

                input_data = None
                if 'data' in input_json:
                    input_data = input_json['data']

                func = Function(id=str(uuid.uuid4()),
                                name=input_name,
                                code=input_code,
                                data=input_data,
                                item_id=item.id)
                db.session.add(func)
                db.session.commit()

                return jsonify(func.to_dict()), 201
        else:

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_read_item(account=account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this item'), 403

            retrieved_funcs = [f.to_dict() for f in Function.query.filter(Function.item_id == item.id)]
            return jsonify(retrieved_funcs)
    else:
        return jsonify([])

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404


@app.route('/items/<id>/functions/<name>', methods=['GET', 'PUT', 'POST', 'DELETE'])
@require_oauth()
def item_function(id, name):
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:
        if request.method == 'POST':
            # function invocation
            if not can_account_execute_item(account=current_token.account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to execute this item'), 403

            func = Function.query.filter(Function.item_id == item.id and Function.name == name).first()

            if func:
                arguments = request.get_json(force=True, silent=False)
                result = dict()
                data = func.data
                safe_list = ['arguments', 'result', 'item', 'request', 'data']
                safe_dict = dict([(k, locals().get(k, None)) for k in safe_list])
                eval(func.code, None, safe_dict)

                return jsonify(result), 200
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='function {0} not found'.format(name)), 404

        elif request.method == 'PUT':

            func = Function.query.filter(Function.item_id == item.id and Function.name == name).first()

            if func:
                input_json = request.get_json(force=True, silent=False)

                if not can_account_write_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to item'), 403

                if 'code' in input_json:
                    func.code = input_json['code']

                if 'data' in input_json:
                    func.data = input_json['data']

                db.session.commit()

                return jsonify(func.to_dict()), 200
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='function {0} not found'.format(name)), 404

        elif request.method == 'DELETE':

            func = Function.query.filter(Function.item_id == item.id and Function.name == name).first()

            if func:
                if not can_account_write_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to item'), 403

                db.session.delete(func)
                db.session.commit()

                return jsonify(isError=False,
                               message="Success",
                               statusCode=200,
                               data='deleted function {0}'.format(name)), 200
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='function {0} not found'.format(name)), 404
        else:
            func = Function.query.filter(Function.item_id == item.id and Function.name == name).first()

            if func:
                if not can_account_read_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to read this item'), 403

                return jsonify(func.to_dict()), 200
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='function {0} not found'.format(name)), 404

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404

@app.route('/items/<id>/topics', methods=['GET', 'POST'])
@require_oauth()
def item_topics(id):
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:

        if request.method == 'POST':
            input_json = request.get_json(force=True, silent=False)

            input_name = input_json['name']
            if input_name:

                if not can_account_write_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to item'), 403

                topic = Topic.query.filter(Topic.item_id == item.id and Topic.name == input_name).first()

                if topic:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=400,
                                   data='A function with the same name already exists'), 400

                input_data = None
                if 'data' in input_json:
                    input_data = input_json['data']

                topic = Topic(id=str(uuid.uuid4()), name=input_name, data=input_data, item_id=item.id)
                db.session.add(topic)
                db.session.commit()

                return jsonify(topic.to_dict()), 201
        else:

            if not can_account_read_item(account=current_token.account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this item'), 403

            retrieved_topics = [t.to_dict() for t in Topic.query.filter(Topic.item_id == item.id)]
            return jsonify(retrieved_topics)
    else:
        return jsonify([])

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404


@app.route('/items/<id>/topics/<name>', methods=['GET', 'PUT', 'POST', 'DELETE'])
@require_oauth()
def item_topic(id, name):
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:
        if request.method == 'POST':

            if not can_account_message_item(account=current_token.account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to message this item'), 403

            topic = Topic.query.filter(Topic.item_id == item.id and Topic.name == name).first()

            if topic:
                input_json = request.get_json(force=True, silent=False)

                msg = Message(id=str(uuid.uuid4()), data=input_json, topic_id=topic.id)

                db.session.add(msg)
                db.session.commit()

                topic = Topic.query.filter(Topic.item_id == id, Topic.name == name).first()

                funcs = [tf.function for tf in TopicFunction.query.filter(TopicFunction.topic_id == topic.id)]

                for func in funcs:
                    arguments = msg
                    result = dict()
                    data = func.data
                    safe_list = ['arguments', 'result', 'item', 'topic']
                    safe_dict = dict([(k, locals().get(k, None)) for k in safe_list])
                    eval(func.code, None, safe_dict)

                return jsonify(msg.to_dict()), 200
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='topic {0} not found'.format(name)), 404
        elif request.method == 'PUT':

            topic = Topic.query.filter(Topic.item_id == item.id and Topic.name == name).first()

            if topic:
                input_json = request.get_json(force=True, silent=False)

                if not can_account_write_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to item'), 403

                if 'data' in input_json:
                    topic.data = input_json['data']

                db.session.commit()

                return jsonify(topic.to_dict()), 200
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='topic {0} not found'.format(name)), 404

        elif request.method == 'DELETE':

            topic = Topic.query.filter(Topic.item_id == item.id and Topic.name == name).first()

            if topic:
                if not can_account_write_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to item'), 403

                db.session.delete(topic)
                db.session.commit()

                return jsonify(isError=False,
                               message="Success",
                               statusCode=200,
                               data='deleted topic {0}'.format(name)), 200
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='function {0} not found'.format(name)), 404
        else:
            topic = Topic.query.filter(Topic.item_id == item.id and Topic.name == name).first()

            if topic:
                if not can_account_read_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to read this item'), 403
                # TODO: sort and paginate messages
                # TODO: add timestamps
                retrieved_msgs = [t.to_dict() for t in Message.query.filter(Message.topic_id == topic.id)]
                return jsonify(retrieved_msgs)
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='topic {0} not found'.format(name)), 404

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404

@app.route('/items/<id>/topics/<topic_name>/functions', methods=['GET', 'POST'])
@require_oauth()
def item_topic_functions(id, topic_name):
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:

        if request.method == 'POST':
            input_json = request.get_json(force=True, silent=False)

            input_name = input_json['name']
            if input_name:

                if not can_account_write_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to item'), 403

                func = Function.query.filter(Function.item_id == item.id, Function.name == input_name).first()

                if func:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=400,
                                   data='A function with the same name already exists'), 400

                input_code = input_json['code']

                input_data = None
                if 'data' in input_json:
                    input_data = input_json['data']

                func_id = str(uuid.uuid4())
                func = Function(id=func_id,name=input_name,code=input_code,data=input_data, item_id=item.id)

                topic = Topic.query.filter(Topic.item_id == id and Topic.name == topic_name).first()

                if topic:
                    if not can_account_write_item(account=current_token.account, item=item):
                        return jsonify(isError=True,
                                       message="Failure",
                                       statusCode=403,
                                       data='Account not authorized to write to this item'), 403
                    db.session.add(func)
                    topic_func = TopicFunction(id=str(uuid.uuid4()), topic_id=topic.id, function_id=func_id)
                    db.session.add(topic_func)
                    db.session.commit()

                    return jsonify(func.to_dict()), 201
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=404,
                                   data='topic {0} not found'.format(name)), 404
        else:
            topic = Topic.query.filter(Topic.item_id == id and Topic.name == name).first()

            if topic:
                if not can_account_read_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to read this item'), 403

                retrieved_funcs = [f.function.to_dict() for f in TopicFunction.query.filter(TopicFunction.topic_id == topic.id)]
                return jsonify(retrieved_funcs)
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='topic {0} not found'.format(name)), 404
    else:
        return jsonify([])

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404


@app.route('/items/<id>/topics/<topic_name>/functions/<func_name>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def topic_function(id, topic_name, func_name):
    # TODO
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:
        func = Function.query.filter(Function.item_id == item.id, Function.name == func_name).first()
        topic = Topic.query.filter(Topic.item_id == id, Topic.name == topic_name).first()

        if func and topic:
            if request.method == 'PUT':
                if not can_account_write_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to this item'), 403

                topic_funcs = TopicFunction.query.filter(TopicFunction.topic_id == topic.id)

                topic_func = next(iter([f for f in topic_funcs if f.function_id == func.id]), None)

                if topic_func:
                    input_json = request.get_json(force=True, silent=False)

                    if 'code' in input_json:
                        func.code = input_json['code']

                    if 'data' in input_json:
                        func.data = input_json['data']

                    db.session.commit()

                    return jsonify(func.to_dict()), 200
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=404,
                                   data='topic function {0} not found'.format(func_name)), 404

            elif request.method == 'DELETE':
                if not can_account_write_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to this item'), 403

                topic_funcs = TopicFunction.query.filter(TopicFunction.topic_id == topic.id)

                

                topic_func = next(iter([f for f in topic_funcs if f.function_id == func.id]), None)

                if topic_func:
                    db.session.delete(topic_func)
                    db.session.delete(func)
                    db.session.commit()

                    return jsonify(isError=False,
                                   message="Success",
                                   statusCode=200,
                                   data='deleted function {0}'.format(func_name)), 200
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=404,
                                   data='topic function {0} not found'.format(func_name)), 404
            else:
                if not can_account_read_item(account=current_token.account, item=item):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to this item'), 403

                topic_funcs = TopicFunction.query.filter(TopicFunction.topic_id == topic.id)

                topic_func = next(iter([f for f in topic_funcs if f.function_id == func.id]), None)

                if topic_func:
                    return jsonify(func.to_dict()), 200
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=404,
                                   data='topic function {0} not found'.format(func_name)), 404
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=404,
                           data='topic {0} not found'.format(topic_name)), 404

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404



@app.route('/items/<id>/items', methods=['GET', 'POST'])
@require_oauth()
def item_items(id):
    item = Item.query.filter(Item.id == id, Item.group_id == current_token.account.group_id).first()
    if item:
        module_name = item.type.module

        if not module_name:
            module_name = 'default'

        module = importlib.import_module('realnet_server.modules.{}'.format(module_name))
        module_class = getattr(module, module_name.capitalize())
        module_instance = module_class()

        if request.method == 'POST':
            input_data = request.get_json(force=True, silent=False)

            input_name = input_data['name']
            if input_name:
                parent_id = id

                parent = Item.query.filter(Item.id == parent_id).first()

                if not parent:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=404,
                                   data='Parent item not found'), 404

                account = Account.query.filter(Account.id == current_token.account.id).first()

                if not can_account_write_item(account=account, item=parent):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to parent'), 403

                input_attributes = None

                if 'attributes' in input_data:
                    input_attributes = input_data['attributes']

                parent_item = Item.query.filter(Item.id == parent_id).first()

                args = dict()

                if input_name:
                    args['name'] = input_name

                if input_attributes:
                    args['attributes'] = input_attributes

                module_instance.create_item(parent_item=parent_item, **args)

                return jsonify(item.to_dict()), 201
        else:

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_read_item(account=account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this item'), 403
            retrieved_items = filter_readable_items(account, module_instance.get_items(item.to_dict()))
            return jsonify(retrieved_items)
    else:
        return jsonify([])

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404

