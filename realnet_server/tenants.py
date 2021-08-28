from flask import request, jsonify, url_for
from authlib.integrations.flask_oauth2 import current_token
from authlib.integrations.flask_client import OAuth
from realnet_server import app
from .auth import authorization, require_oauth
from .models import db, Group, Account, AccountType, GroupRoleType, create_tenant, Authenticator, get_or_create_delegated_account
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
    group = Group.query.filter(or_(Group.id == id, Group.name == id), Group.parent_id == None).first()
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

@app.route('/tenants/<id>/login/<name>')
def tenant_login(id, name):
    # 1. get the group
    group = Group.query.filter(or_(Group.id == id, Group.name == id), Group.parent_id == None).first()
    if group:
        auth = Authenticator.query.filter(Authenticator.name == name, Authenticator.group_id == group.id).first()

        if auth:
            oauth = OAuth(app)
            data = auth.to_dict()
            del data['name']
            del data['id']
            backend = oauth.register(auth.name, **data)
            redirect_uri = url_for('tenant_auth', _external=True, id=id, name=name)
            return backend.authorize_redirect(redirect_uri)

        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=404,
                           data='Authenticator {0} not found'.format(name)), 404

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='Tenant {0} not found'.format(id)), 404

@app.route('/tenants/<id>/auth/<name>')
def tenant_auth(id, name):
    # 1. get the group
    group = Group.query.filter(or_(Group.id == id, Group.name == id), Group.parent_id == None).first()
    if group:
        auth = Authenticator.query.filter(Authenticator.name == name, Authenticator.group_id == group.id).first()

        if auth:
            oauth = OAuth(app)
            data = auth.to_dict()
            del data['name']
            del data['id']
            backend = oauth.register(auth.name, **data)
            token = backend.authorize_access_token()
            if token:
                userinfo = backend.get(auth.userinfo_endpoint, token=token)
                if userinfo:
                    userinfo_data = userinfo.json()
                    email = userinfo_data['email']
                    external_id = '{}:{}'.format(auth.name, userinfo_data.get('sub', userinfo_data.get('id', None)))
                    user = get_or_create_delegated_account(id,
                                                           'person',
                                                           'guest',
                                                           email,
                                                           email,
                                                           external_id)
                    if user:
                        return authorization.create_authorization_response(grant_user=user)
                    else:
                        return jsonify(isError=True,
                                       message="Failure",
                                       statusCode=401,
                                       data='Invalid user'), 401
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=400,
                                   data='Cannot retrieve user profile info'), 400
            else:
                return jsonify(isError=True,
                        message="Failure",
                        statusCode=401,
                        data='Invalid token'), 401

        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=404,
                           data='Authenticator {0} not found'.format(name)), 404

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='Tenant {0} not found'.format(id)), 404


