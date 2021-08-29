from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, Group, Account, App, create_app
from sqlalchemy import or_
import uuid

def can_account_create_app(account):
    return True

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
            input_uri = input_data['uri']
            input_scope = input_data['scope']
            input_auth_method = input_data['auth_method']
            input_grant_types = input_data['grant_types']
            input_redirect_uris = input_data['redirect_uris']
            input_response_types = input_data['response_types']

            if input_name  and input_uri and input_auth_method:

                if not can_account_create_app(current_token.account):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to create the app'), 403

                created = create_app(input_name,
                                     input_uri,
                                     input_grant_types,
                                     input_redirect_uris,
                                     input_scope,
                                     input_auth_method,
                                     input_response_types,
                                     current_token.account.id,
                                     current_token.account.group_id)

                if created:
                    return jsonify(created.to_dict()), 201
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=400,
                                   data='Cannot create the app'), 400
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=402,
                               data='Bad request, missing name, group, uri or auth_method parameter'), 402
    else:
        return jsonify([q.to_dict() for q in App.query.filter(App.group_id == current_token.account.group_id)])

@app.route('/apps/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_app(id):
    app = App.query.filter(or_(App.id == id, App.name == id),
                           App.group_id == current_token.account.group_id).first()
    if app:
        if request.method == 'PUT':

            if not can_account_write_app(account=current_token.account, app=app):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to write to app'), 403

            client_metadata = app.client_metadata

            input_data = request.get_json(force=True, silent=False)

            if 'name' in input_data:
                app.name = input_data['name']
                client_metadata['client_name'] = input_data['name']

            if 'uri' in input_data:
                client_metadata['client_uri'] = input_data['uri']

            if 'grant_types' in input_data:
                client_metadata['grant_types'] = input_data['grant_types']

            if 'redirect_uris' in input_data:
                client_metadata['redirect_uris'] = input_data['redirect_uris']

            if 'response_types' in input_data:
                client_metadata['response_types'] = input_data['response_types']

            if 'scope' in input_data:
                client_metadata['scope'] = input_data['scope']

            app.client_metadata = client_metadata

            db.session.commit()

            return jsonify(app.to_dict())

        elif request.method == 'DELETE':

            if not can_account_delete_app(account=current_token.account, app=app):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to delete this app'), 403

            db.session.delete(app)
            db.session.commit()

            return jsonify(isError=False,
                           message="Success",
                           statusCode=200,
                           data='deleted app {0}'.format(id)), 200
        else:
            if not can_account_read_app(account=current_token.account, app=app):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this app'), 403
            return jsonify(app.to_dict())


    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='app {0} not found'.format(id)), 404

