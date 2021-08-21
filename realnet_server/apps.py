from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, Group, Account, AccountGroup, GroupRoleType
from sqlalchemy import or_
import uuid

def can_account_read_app(account, app):
    return True

def can_account_write_app(account, app):
    return True

def can_account_delete_app(account, app):
    return True

@app.route('/apps', methods=('GET', 'POST'))
@require_oauth()
def apps():
    if request.method == 'POST':
        request.on_json_loading_failed = lambda x: print('json parsing error: ', x)
        input_data = request.get_json(force=True, silent=False)
        if input_data:
            input_name = input_data['name']
            if input_name:
                created = Group(id=str(uuid.uuid4()),
                                name=input_name)

                db.session.add(created)
                db.session.commit()

                return jsonify(created.to_dict()), 201
    else:
        return jsonify([q.to_dict() for q in Group.query.all()])

@app.route('/apps/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_app(id):
    # 1. get the group
    group = Group.query.filter(or_(Group.id == id, Group.name == id)).first()
    if group:
        
        if request.method == 'PUT':

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_write_app(account=account, app=None):
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

            if not can_account_delete_app(account=account, app=None):
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

            if not can_account_read_app(account=account, app=None):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this group'), 403
            return jsonify(group.to_dict())

    return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='get_item {0}'.format(id)), 404

