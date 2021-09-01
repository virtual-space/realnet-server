from flask import request, jsonify, url_for, redirect, render_template
from authlib.integrations.flask_oauth2 import current_token
from authlib.integrations.flask_client import OAuth
from authlib.integrations.requests_client import OAuth2Session
from realnet_server import app
from .auth import authorization, require_oauth
from .models import db, Group, Account, AccountGroup, GroupRoleType, Token, App, create_tenant, Authenticator, get_or_create_delegated_account
from sqlalchemy import or_
from password_generator import PasswordGenerator
try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from authlib.common.urls import url_encode


def can_account_create_tenant(account):
    for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                  AccountGroup.account_id == account.id):
        if accountGroup.role_type == GroupRoleType.root:
            return True

def can_account_read_tenant(account, tenant):
    if account.group_id == tenant.id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root:
                return True

    return False

def can_account_write_tenant(account, tenant):
    if account.group_id == tenant.id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root:
                return True

    return False

def can_account_delete_tenant(account, tenant):
    if account.group_id == tenant.id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root:
                return True

    return False

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
        if not can_account_create_tenant(account=current_token.account):
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=403,
                           data='Account not authorized to read tenants'), 403
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

@app.route('/tenants/<id>/clients/<client_id>/login',methods=['GET', 'POST'] )
def tenant_login_password(id, client_id):
    # 1. get the group
    group = Group.query.filter(or_(Group.id == id, Group.name == id), Group.parent_id == None).first()
    if group:
        client = App.query.filter(App.name == client_id, App.group_id == group.id).first()
        if client:
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                account = Account.query.filter_by(username=username).first()
                if account is not None and account.check_password(password):
                    return authorization.create_authorization_response(grant_user=account)
                    token = authorization.generate_token(client.id, 'password')
                    t = Token(
                        client_id=client_id,
                        user_id=account.id,
                        **token
                    )
                    db.session.add(t)
                    db.session.commit()
                    redirect_uri = ''
                    if client.redirect_uris:
                        redirect_uri = client.redirect_uris[0]
                    if redirect_uri:
                        params = [(k, token[k]) for k in token]
                        uri = add_params_to_uri(redirect_uri, params, fragment=True)
                        return redirect(uri)
                    else:
                        return jsonify(token)
                else:
                    return render_template('login.html')
            else:
                return render_template('login.html')
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=404,
                           data='Client {0} not found'.format(client_id)), 404

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='Tenant {0} not found'.format(id)), 404

def add_params_to_qs(query, params):
    """Extend a query with a list of two-tuples."""
    if isinstance(params, dict):
        params = params.items()

    qs = urlparse.parse_qsl(query, keep_blank_values=True)
    qs.extend(params)
    return url_encode(qs)

def add_params_to_uri(uri, params, fragment=False):
    """Add a list of two-tuples to the uri query components."""
    sch, net, path, par, query, fra = urlparse.urlparse(uri)
    if fragment:
        fra = add_params_to_qs(fra, params)
    else:
        query = add_params_to_qs(query, params)
    return urlparse.urlunparse((sch, net, path, par, query, fra))


@app.route('/tenants/<id>/clients/<client_id>/register', methods=('GET', 'POST'))
def tenant_register(id, client_id):
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        account1 = Account.query.filter_by(username=username).first()
        account2 = Account.query.filter_by( email=email).first()
        if account1 or account2:
            return render_template('register.html')
        else:
            # account = Account(id=str(uuid.uuid4()), username=username, email=email)
            # account.set_password(password)
            # db.session.add(account)
            # db.session.commit()
            # if user is not just to log in, but need to head back to the auth page, then go for it
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect('/')
    else:
        return render_template('register.html')

@app.route('/tenants/<id>/clients/<client_id>/auth/<name>')
def tenant_auth(id, client_id, name):
    # 1. get the group
    group = Group.query.filter(or_(Group.id == id, Group.name == id), Group.parent_id == None).first()
    if group:
        client = App.query.filter(App.name == client_id, App.group_id == group.id).first()
        if client:
            auth = Authenticator.query.filter(Authenticator.name == name, Authenticator.group_id == group.id).first()
            if auth:
                if name:
                    oauth = OAuth(app)
                    data = auth.to_dict()
                    del data['name']
                    del data['id']
                    print(request)
                    code = request.args.get('code')
                    token = None
                    if code:
                        oaclient = OAuth2Session(auth.client_id, auth.client_secret, scope=request.args.get('scope'))
                        token_endpoint = 'https://oauth2.googleapis.com/token'
                        try:
                            token_test = oaclient.fetch_token(token_endpoint, authorization_response=request.url)
                            print(token_test)
                        except Exception as e:
                            print('error while fetching token {}'.format(e))

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
                                # return authorization.create_token_response()
                                # client.
                                token = authorization.generate_token('auth', 'implicit')
                                t = Token(
                                    client_id='auth',
                                    user_id=user.id,
                                    **token
                                )
                                db.session.add(t)
                                db.session.commit()
                                redirect_uri = ''
                                if client.redirect_uris:
                                    redirect_uri = client.redirect_uris[0]
                                params = [(k, token[k]) for k in token]
                                uri = add_params_to_uri(redirect_uri, params, fragment=True)
                                return redirect(uri)
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
                    pass

            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='Authenticator {0} not found'.format(name)), 404
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=404,
                           data='Client {0} not found'.format(client_id)), 404

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='Tenant {0} not found'.format(id)), 404

@app.route('/tenants/<id>/auth', methods=['GET'])
def tenant_auths(id):
    group = Group.query.filter(or_(Group.id == id, Group.name == id), Group.parent_id == None).first()
    if group:
        return jsonify([{ 'name': n['name'], 'type': 'oauth'} for n in [q.to_dict() for q in Authenticator.query.filter(Authenticator.group_id == group.id)]])
    else:
        return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='Tenant {0} not found'.format(id)), 404