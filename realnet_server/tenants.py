from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, Group, Account, create_tenant
from sqlalchemy import or_
from password_generator import PasswordGenerator
import uuid

def can_account_create_tenant(account):
    return True

def can_account_read_tenant(account, tenant):
    return True

def can_account_write_tenant(account, tenant):
    return True

def can_account_delete_tenant(account, tenant):
    return True

@app.route('/tenants', methods=('GET', 'POST'))
@require_oauth()
def tenants():
    if request.method == 'POST':
        request.on_json_loading_failed = lambda x: print('json parsing error: ', x)
        input_data = request.get_json(force=True, silent=False)
        if input_data:
            input_name = input_data['name']
            account = Account.query.filter(Account.id == current_token.account.id).first()
            if not can_account_create_tenant(account=account):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to create tenant'), 403
            if input_name:
                root_username = 'root'
                root_email = 'root@localhost'
                pwo = PasswordGenerator()
                pwo.minlen = 8  # (Optional)
                pwo.maxlen = 8  # (Optional)
                root_password = pwo.generate()

                if 'username' in input_data:
                    root_username = input_data['username']

                if 'password' in input_data:
                    root_password = input_data['password']

                if 'email' in input_data:
                    root_email = input_data['email']

                created = create_tenant(input_name, root_username, root_email, root_password)
                return jsonify(created), 201
    else:
        return jsonify([q.to_dict() for q in Group.query.filter(Group.parent_id == None)])

@app.route('/tenants/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_tenant(id):
    # 1. get the group
    group = Group.query.filter(or_(Group.id == id, Group.name == id)).first()
    if group:
        
        if request.method == 'PUT':

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_write_tenant(account=account, tenant=group):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to write to tenant'), 403

            input_data = request.get_json(force=True, silent=False)

            args = dict()

            if 'name' in input_data:
                group.name = input_data['name']
            
            db.session.commit()
            
            return jsonify(group.to_dict())

        elif request.method == 'DELETE':

            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_delete_tenant(account=account, tenant=group):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to delete this tenant'), 403

            db.session.delete(group)
            db.session.commit()

            return jsonify(isError=False,
                           message="Success",
                           statusCode=200,
                           data='deleted item {0}'.format(id)), 200
        else:
            account = Account.query.filter(Account.id == current_token.account.id).first()

            if not can_account_read_tenant(account=account, tenant=group):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this tenant'), 403
            return jsonify(group.to_dict())

    return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Tenant {0} not found'.format(id)), 404


