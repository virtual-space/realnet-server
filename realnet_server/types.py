from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, Type, Group, Account
from sqlalchemy import or_
import uuid

def can_account_create_type(account, group):
    return True

def can_account_read_type(account, type):
    return True

def can_account_write_type(account, type):
    return True

def can_account_delete_type(account, type):
    return True

@app.route('/types', methods=('GET', 'POST'))
@require_oauth()
def types():
    if request.method == 'POST':
        request.on_json_loading_failed = lambda x: print('json parsing error: ', x)
        input_data = request.get_json(force=True, silent=False)
        if input_data:
            input_name = input_data['name']
            if input_name:
                parent_id = None

                if 'parent_id' in input_data:
                    parent_id = input_data['parent_id']

                    parent = Type.query.filter(Type.id == parent_id).first()
                    if not parent:
                        return jsonify(isError=True,
                                       message="Failure",
                                       statusCode=404,
                                       data='Parent type not found'), 404

                input_attributes = None

                if 'attributes' in input_data:
                    input_attributes = input_data['attributes']

                input_module = 'default'

                if 'module' in input_data:
                    input_module = input_data['module']

                parent_type = None

                if parent_id:
                    parent_type = Type.query.filter(Type.id == parent_id).first()

                created_type = Type(id=str(uuid.uuid4()),
                                    name=input_name,
                                    attributes=input_attributes,
                                    owner_id=current_token.account.id,
                                    group_id=current_token.account.group_id,
                                    module=input_module)

                db.session.add(created_type)
                db.session.commit()

                return jsonify(created_type.to_dict()), 201
    else:
        return jsonify([q.to_dict() for q in Type.query.all()])


@app.route('/types/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_type(id):
    # 1. get the group
    group = Group.query.filter(or_(Group.id == id, Group.name == id)).first()
    if group:

        if request.method == 'PUT':

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_write_type(account=account, type=None):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to write to group'), 403

            input_data = request.get_json(force=True, silent=False)

            args = dict()

            if 'name' in input_data:
                group.name = input_data['name']

            db.session.commit()

            return jsonify(group.to_dict())

        elif request.method == 'DELETE':

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_delete_type(account=account, type=None):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to delete this group'), 403

            db.session.delete(group)
            db.session.commit()

            return jsonify(isError=False,
                           message="Success",
                           statusCode=200,
                           data='deleted item {0}'.format(id)), 200
        else:
            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_read_type(account=account, type=None):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this group'), 403
            return jsonify(group.to_dict())

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='get_item {0}'.format(id)), 404