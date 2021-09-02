from authlib.integrations.flask_client import OAuth
from authlib.oidc.core import UserInfo
from .auth import authorization, require_oauth
from realnet_server import app
from flask import request, session
from flask import render_template, jsonify
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error
from .models import Account

import pprint

oauth = OAuth(app)


@app.route('/settings')
def settings():
    account = current_user()
    return render_template('settings.html',account=account)

@app.route('/error')
def error():
    return render_template('error.html')

def current_user():
    if 'id' in session:
        uid = session['id']
        return Account.query.get(uid)
    return None

def split_by_crlf(s):
    return [v for v in s.splitlines() if v]

@app.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    user = current_user()

    if request.method == 'GET':
        try:
            grant = authorization.validate_consent_request(end_user=user)
        except OAuth2Error as error:
            return jsonify(dict(error.get_body()))
        return render_template('authorize.html', user=user, grant=grant)

    if not user and 'username' in request.form:
        username = request.form.get('username')
        user = Account.query.filter_by(username=username).first()
    if request.form['confirm']:
        grant_user = user
    else:
        grant_user = None

    print('/oauth/authorize called')
    print(request.url)
    return authorization.create_authorization_response(grant_user=grant_user)

@app.route('/oauth/token', methods=['POST'])
def issue_token():
    print('*** issue token called')
    print(pprint.pformat(request.environ, depth=5))
    return authorization.create_token_response()


@app.route('/oauth/revoke', methods=['POST'])
def revoke_token():
    return authorization.create_endpoint_response('revocation')


@app.route('/oauth/userinfo')
@require_oauth('profile')
def api_me():
    print('*** userinfo called')
    print(request.url)
    return jsonify(UserInfo(sub=str(current_token.user.id), name=current_token.user.username))


