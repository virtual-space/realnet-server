from authlib.integrations.flask_client import OAuth
from .auth import authorization
from realnet_server import app

oauth = OAuth(app)


@app.route('/oauth/token', methods=['POST'])
def issue_token():
    return authorization.create_token_response()


@app.route('/oauth/revoke', methods=['POST'])
def revoke_token():
    return authorization.create_endpoint_response('revocation')


