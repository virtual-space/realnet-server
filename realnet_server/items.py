from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from flask import request, jsonify, send_file
from .models import db, Item, Type, Account, AccountGroup, Acl, AclType
from .auth import require_oauth
import importlib
import json
import uuid


def can_account_read_item(account, item):
    if [acl for acl in item.acls if acl.type == AclType.public]:
        return True

    if [acl for acl in item.acls if acl.type == AclType.user and acl.name == account.username and ('r' in acl.permission or 'w' in acl.permission)]:
        return True

    account_groups = set([ag.name for ag in AccountGroup.query.filter(AccountGroup.account_id == account.id)])

    if [acl for acl in item.acls if acl.type == AclType.group and acl.name in account_groups and ('r' in acl.permission or 'w' in acl.permission)]:
        return True

    account_group = AccountGroup.query.filter(AccountGroup.group_id == item.group_id and AccountGroup.account_id == account.id).first()

    if account_group:
        return True

    if item.owner_id == account.id:
        return True


def can_account_write_item(account, item):
    if [acl for acl in item.acls if
        acl.type == AclType.user and acl.name == account.username and 'w' in acl.permission]:
        return True

    account_groups = set([ag.name for ag in AccountGroup.query.filter(AccountGroup.account_id == account.id)])

    if [acl for acl in item.acls if
        acl.type == AclType.group and acl.name in account_groups and 'w' in acl.permission]:
        return True

    account_group = AccountGroup.query.filter(
        AccountGroup.group_id == item.group_id and AccountGroup.account_id == account.id).first()

    if account_group:
        return True

    if item.owner_id == account.id:
        return True


def can_account_delete_item(account, item):
    account_group = AccountGroup.query.filter(
        AccountGroup.group_id == item.group_id and AccountGroup.account_id == account.id).first()
    if account_group:
        return True
    return item.owner_id == account.id


def filter_readable_items(account, items_json):
    return [i for i in json.parse(items_json) if can_account_read_item(account, i)]


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

                    parent_item = None

                    if parent_id:
                        parent_item = Item.query.filter(Item.id == parent_id).first()

                    args = dict()

                    if input_name:
                        args['name'] = input_name

                    if input_attributes:
                        args['attributes'] = input_attributes

                    args['owner_id'] = current_token.account.id
                    args['group_id'] = current_token.account.group_id
                    args['type_id'] = input_type.id

                    created_item = module_instance.create_item(parent_item=parent_item, **args)

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
        return jsonify([i.to_dict() for i in Item.query.filter(Item.parent_id == None)]), 200


@app.route('/items/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_item(id):
    # 1. get the type
    item = Item.query.filter(Item.id == id).first()
    if item:
        module_name = item.type.module

        if not module_name:
            module_name = 'default'

        module = importlib.import_module('realnet_server.modules.{}'.format(module_name))
        module_class = getattr(module, module_name.capitalize())
        module_instance = module_class()

        if request.method == 'PUT':

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_write_item(account=account, item=item):
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

                if not can_account_write_item(account=account, item=parent):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to parent'), 403


            if 'attributes' in input_data:
                args['attributes'] = input_data['attributes']

            module_instance.update_item(item, **args)

            return jsonify(item.to_dict())

        elif request.method == 'DELETE':

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_delete_item(account=account, item=item):
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
            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_read_item(account=account, item=item):
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


ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif'}


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/items/<id>/data', methods=['GET', 'PUT', 'POST', 'DELETE'])
@require_oauth()
def item_data(id):
    item = Item.query.filter(Item.id == id).first()
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
                module_instance.update_item_data(item, file)
                # file.save(os.path.join(UPLOAD_FOLDER, filename))
                return jsonify({'url': '/items/{}/data'.format(item.id)})

        elif request.method == 'DELETE':

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_write_item(account=account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to delete data from this item'), 403

            module_instance.delete_item_data(item)
            return jsonify(isError=False,
                           message="Success",
                           statusCode=200,
                           data='deleted item {0}'.format(id)), 200
        else:
            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_read_item(account=account, item=item):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read data from this item'), 403

            output_filename = module_instance.get_item_data(item)

        if output_filename:
            return send_file(output_filename, as_attachment=True)
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
    item = Item.query.filter(Item.id == id).first()
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
                jsonify([a.to_dict() for a in Acl.query.filter(Acl.item_id == item.id)])
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
    item = Item.query.filter(Item.id == id).first()
    if item:
        if item.owner_id == current_token.account.id or item.group_id == current_token.account.group_id:
            acl = Acl.query.filter(Acl.id == aclid and Acl.item_id == id).first()
            if acl:
                if request.method == 'GET':
                    return jsonify(acl.to_dict()), 200
                elif request.method == 'DELETE':
                    db.session.delete(item)
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


@app.route('/items/<id>/items', methods=['GET', 'POST'])
@require_oauth()
def item_items(id):
    item = Item.query.filter(Item.id == id).first()
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

            retrieved_items = filter_readable_items(account, module_instance.get_items(item))
            return retrieved_items
    else:
        return jsonify([])

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404



