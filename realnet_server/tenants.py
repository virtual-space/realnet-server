from flask import request, jsonify, url_for, redirect, render_template
from authlib.integrations.flask_oauth2 import current_token
from authlib.integrations.flask_client import OAuth
from authlib.integrations.requests_client import OAuth2Session
from authlib.common.encoding import to_unicode, to_bytes
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

@app.route('/<id>/login', defaults={'name': None}, methods=['GET', 'POST'] )
@app.route('/<id>/login/<name>',methods=['GET', 'POST'] )
def tenant_login(id, name):
    # 1. get the group
    print(request.url)
    group = Group.query.filter(or_(Group.id == id, Group.name == id), Group.parent_id == None).first()
    if group:
        client_id = request.args.get('client_id')
        response_type = request.args.get('response_type')
        client = App.query.filter(or_(App.client_id == client_id, App.name == client_id, App.group_id == group.id)).first()
        if client:
            if request.method == 'POST':
                username = request.form.get('username')
                password = request.form.get('password')
                account = Account.query.filter_by(username=username).first()
                if account is not None and account.check_password(password):
                    return authorization.create_authorization_response(grant_user=account)
            else:
                if name == None:
                    oauths = [{'name': n['name'],
                               'url': '/{0}/login/{1}?client_id={2}&response_type={3}'.format(id, n['name'], client_id, response_type)} for n in
                              [q.to_dict() for q in Authenticator.query.filter(Authenticator.group_id == group.id)]]

                    return render_template('login.html', authenticators=oauths, client_id=client_id)
                else:
                    auth = Authenticator.query.filter(Authenticator.name == name,
                                                      Authenticator.group_id == group.id).first()
                    if auth:
                        print(auth)
                        oauth = OAuth(app)
                        data = auth.to_dict()
                        del data['name']
                        del data['id']
                        backend = oauth.register(auth.name, **data)
                        redirect_uri = url_for('tenant_auth', _external=True, id=id, client_id=client_id, name=name, response_type=response_type)
                        print(redirect_uri)
                        return backend.authorize_redirect(redirect_uri=redirect_uri)
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


@app.route('/<id>/<client_id>/register', methods=('GET', 'POST'))
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

@app.route('/<id>/authorize/<name>', defaults={'client_id': None})
@app.route('/<id>/<client_id>/authorize/<name>')
def tenant_auth(id, client_id, name):
    # 1. get the
    print(request.url)
    group = Group.query.filter(or_(Group.id == id, Group.name == id), Group.parent_id == None).first()
    if group:
        if client_id is None:
            client_id = request.args.get('client_id')
        client = App.query.filter(or_(App.client_id == client_id, App.name == client_id), App.group_id == group.id).first()
        if client:
            auth = Authenticator.query.filter(Authenticator.name == name, Authenticator.group_id == group.id).first()
            if auth:
                    data = auth.to_dict()
                    del data['name']
                    del data['id']
                    print(request)
                    code = request.args.get('code')
                    response_type = request.args.get('response_type')
                    if code:
                        oaclient = OAuth2Session(auth.client_id, auth.client_secret, scope=request.args.get('scope'))
                        token_endpoint = auth.access_token_url
                        try:
                            redirect_uri = url_for('tenant_auth', _external=True, id=id, client_id=client_id, name=name, response_type=response_type)
                            token_test = oaclient.fetch_token(token_endpoint, authorization_response=request.url, redirect_uri=redirect_uri)
                            if token_test:
                                headers = {'Authorization': 'Bearer ' + token_test['access_token']}
                                userinfo = oaclient.get(auth.userinfo_endpoint, headers=headers)
                                if userinfo:
                                    userinfo_data = userinfo.json()
                                    email = userinfo_data['email']
                                    external_id = '{}:{}'.format(auth.name, userinfo_data.get('sub',
                                                                                              userinfo_data.get('id',
                                                                                                                None)))
                                    user = get_or_create_delegated_account(id,
                                                                           'person',
                                                                           'guest',
                                                                           email,
                                                                           email,
                                                                           external_id)
                                    if user:
                                        request.query_string = to_bytes(to_unicode(request.query_string) + '&client_id={}'.format(client_id))
                                        return authorization.create_authorization_response(request=request, grant_user=user)
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

                        except Exception as e:
                            print('error while fetching token {}'.format(e))
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

@app.route('/<id>/auth', methods=['GET'])
def tenant_auths(id):
    group = Group.query.filter(or_(Group.id == id, Group.name == id), Group.parent_id == None).first()
    if group:
        oauths = [{ 'name': n['name'], 'type': 'oauth'} for n in [q.to_dict() for q in Authenticator.query.filter(Authenticator.group_id == group.id)]]
        oauths.append({'name': 'password', 'type': 'password'})
        return jsonify(oauths)
    else:
        return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='Tenant {0} not found'.format(id)), 404