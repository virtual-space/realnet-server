from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, AccountGroup, GroupRoleType, Authenticator
from sqlalchemy import or_
import uuid


def can_account_create_authenticator(account):
    for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                  AccountGroup.account_id == account.id):
        if accountGroup.role_type == GroupRoleType.root or accountGroup.role_type == GroupRoleType.admin:
            return True

    return False


def can_account_read_authenticator(account, authenticator):
    if account.group_id == authenticator.group_id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root or accountGroup.role_type == GroupRoleType.admin:
                return True

    return False


def can_account_write_authenticator(account, authenticator):
    if account.group_id == authenticator.group_id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root or accountGroup.role_type == GroupRoleType.admin:
                return True

    return False


def can_account_delete_authenticator(account, authenticator):
    if account.group_id == authenticator.group_id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root or accountGroup.role_type == GroupRoleType.admin:
                return True

    return False


@app.route('/authenticators', methods=('GET', 'POST'))
@require_oauth()
def authenticators():
    if request.method == 'POST':
        request.on_json_loading_failed = lambda x: print('json parsing error: ', x)
        input_data = request.get_json(force=True, silent=False)
        if input_data:
            input_name = input_data['name']
            if not can_account_create_authenticator(account=current_token.account):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to create authenticator'), 403
            if input_name:

                args = dict()

                if input_name:
                    args['name'] = input_name

                if 'api_base_url' in input_data:
                    args['api_base_url'] = input_data['api_base_url']

                if 'request_token_url' in input_data:
                    args['request_token_url'] = input_data['request_token_url']

                if 'access_token_url' in input_data:
                    args['access_token_url'] = input_data['access_token_url']

                if 'authorize_url' in input_data:
                    args['authorize_url'] = input_data['authorize_url']

                if 'client_kwargs' in input_data:
                    args['client_kwargs'] = input_data['client_kwargs']

                if 'userinfo_endpoint' in input_data:
                    args['userinfo_endpoint'] = input_data['userinfo_endpoint']

                if 'client_id' in input_data:
                    args['client_id'] = input_data['client_id']

                if 'client_secret' in input_data:
                    args['client_secret'] = input_data['client_secret']

                if 'server_metadata_url' in input_data:
                    args['server_metadata_url'] = input_data['server_metadata_url']

                args['owner_id'] = current_token.account.id
                args['group_id'] = current_token.account.group_id

                created = Authenticator(id=str(uuid.uuid4()),
                                        ** args)

                db.session.add(created)
                db.session.commit()

                return jsonify(created.to_dict()), 201
    else:
        if not can_account_create_authenticator(account=current_token.account):
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=403,
                           data='Account not authorized to read authenticators'), 403
        return jsonify([q.to_dict() for q in Authenticator.query.filter(Authenticator.group_id == current_token.account.group_id)])

@app.route('/authenticators/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_authenticator(id):
    # 1. get the authenticator
    auth = Authenticator.query.filter(or_(Authenticator.id == id, Authenticator.name == id), Authenticator.group_id == current_token.account.group_id).first()
    if auth:
        
        if request.method == 'PUT':

            if not can_account_write_authenticator(account=current_token.account, authenticator=auth):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to write to authenticator'), 403

            input_data = request.get_json(force=True, silent=False)

            if 'api_base_url' in input_data:
                auth.api_base_url = input_data['api_base_url']

            if 'request_token_url' in input_data:
                auth.request_token_url = input_data['request_token_url']

            if 'access_token_url' in input_data:
                auth.access_token_url = input_data['access_token_url']

            if 'authorize_url' in input_data:
                auth.authorize_url = input_data['authorize_url']

            if 'client_kwargs' in input_data:
                auth.client_kwargs = input_data['client_kwargs']

            if 'userinfo_endpoint' in input_data:
                auth.userinfo_endpoint = input_data['userinfo_endpoint']

            if 'client_id' in input_data:
                auth.client_id = input_data['client_id']

            if 'client_secret' in input_data:
                auth.client_secret = input_data['client_secret']

            if 'server_metadata_url' in input_data:
                auth.server_metadata_url = input_data['server_metadata_url']

            
            db.session.commit()
            
            return jsonify(auth.to_dict())

        elif request.method == 'DELETE':

            if not can_account_delete_authenticator(account=current_token.account, authenticator=auth):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to delete this authenticator'), 403

            db.session.delete(auth)
            db.session.commit()

            return jsonify(isError=False,
                           message="Success",
                           statusCode=200,
                           data='deleted authenticator {0}'.format(id)), 200
        else:
            if not can_account_read_authenticator(account=current_token.account, authenticator=auth):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this authenticator'), 403
            return jsonify(auth.to_dict())

    return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Authenticator {0} not found'.format(id)), 404


