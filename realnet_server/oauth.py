from authlib.integrations.flask_client import OAuth
from authlib.oauth2 import OAuth2Error
from authlib.oidc.core import UserInfo
from flask import jsonify, request, render_template
from authlib.integrations.flask_oauth2 import current_token
from .auth import authorization, require_oauth
from realnet_server import app

oauth = OAuth(app)

@app.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    '''
    user = current_user()

    if request.method == 'GET':
        try:
            grant = authorization.validate_consent_request(end_user=user)
        except OAuth2Error as error:
            return jsonify(dict(error.get_body()))
        return render_template('authorize.html', user=user, grant=grant)

    if not user and 'username' in request.form:
        username = request.form.get('username')
        user = User.query.filter_by(username=username).first()
    if request.form['confirm']:
        grant_user = user
    else:
        grant_user = None
    '''
    grant_user = None
    return authorization.create_authorization_response(grant_user=grant_user)

@app.route('/oauth/token', methods=['POST'])
def issue_token():
    return authorization.create_token_response()


@app.route('/oauth/revoke', methods=['POST'])
def revoke_token():
    return authorization.create_endpoint_response('revocation')


@app.route('/oauth/userinfo')
@require_oauth('profile')
def api_me():
    return jsonify(UserInfo(sub=str(current_token.user.id), name=current_token.user.username))


