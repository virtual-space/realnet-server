from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, Group, Account, create_account
from sqlalchemy import or_
import uuid

def can_account_read_accounts(account, group):
    return True

def can_account_write_accounts(account, group):
    return True

def can_account_delete_accounts(account, group):
    return True

@app.route('/accounts', methods=('GET', 'POST'))
@require_oauth()
def accounts():
    if request.method == 'POST':
        request.on_json_loading_failed = lambda x: print('json parsing error: ', x)
        input_data = request.get_json(force=True, silent=False)
        if input_data:
            input_username = input_data['username']
            input_password = input_data['password']
            input_type = input_data['type']
            input_group = input_data['group']
            input_role = input_data['role']
            input_email = input_data['email']

            if input_username and input_password and input_group and input_role and input_email:
                group = db.session.query(Group).filter(Group.name == input_group).first()

                if not group:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=4,
                                   data='Group {} not found'.format(input_group)), 404

                if not can_account_write_accounts(current_token.account, group):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to group'), 403

                created = create_account(input_group,
                                         input_type,
                                         input_role,
                                         input_username,
                                         input_password,
                                         input_email)

                if created:
                    return jsonify(created.to_dict()), 201
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=400,
                                   data='Cannot create the account'), 400
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=402,
                               data='Bad request, missing username, password, group, email, type or role parameter'), 402
    else:
        return jsonify([q.to_dict() for q in Account.query.all()])

@app.route('/accounts/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_account(id):
    # 1. get the group
    group = Group.query.filter(or_(Group.id == id, Group.name == id)).first()
    if group:
        
        if request.method == 'PUT':

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_write_accounts(account=account, group=group):
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

            if not can_account_delete_accounts(account=account, group=group):
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

            if not can_account_read_accounts(account=account, group=group):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this group'), 403
            return jsonify(group.to_dict())

    return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='get_item {0}'.format(id)), 404

