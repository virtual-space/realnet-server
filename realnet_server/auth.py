from authlib.integrations.flask_oauth2 import (
    AuthorizationServer,
    ResourceProtector,
)
from authlib.integrations.sqla_oauth2 import (
    create_query_client_func,
    create_save_token_func,
    create_revocation_endpoint,
    create_bearer_token_validator,
)
from authlib.oauth2.rfc6749 import grants
from authlib.oauth2.rfc7636 import CodeChallenge
from authlib.oidc.core import UserInfo
import authlib.oidc.core.grants as oidc_grants
from werkzeug.security import gen_salt


from .models import db, Account
from .models import App, AuthorizationCode, Token


class AuthorizationCodeGrant(grants.AuthorizationCodeGrant):
    TOKEN_ENDPOINT_AUTH_METHODS = [
        'client_secret_basic',
        'client_secret_post',
        'none',
    ]

    def save_authorization_code(self, code, request):
        print('*** authorization_code_grant:save_authorization_code ***')
        code_challenge = request.data.get('code_challenge')
        code_challenge_method = request.data.get('code_challenge_method')

        if request.data.get('nonce'):
            auth_code = AuthorizationCode(
                code=code,
                client_id=request.client.client_id,
                redirect_uri=request.redirect_uri,
                scope=request.scope,
                account_id=request.user.id,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method,
                nonce=request.data.get('nonce'))
        else:
            auth_code = AuthorizationCode(
                code=code,
                client_id=request.client.client_id,
                redirect_uri=request.redirect_uri,
                scope=request.scope,
                account_id=request.user.id,
                code_challenge=code_challenge,
                code_challenge_method=code_challenge_method)

        db.session.add(auth_code)
        db.session.commit()
        return auth_code

    def query_authorization_code(self, code, client):
        print('*** authorization_code_grant:query_authorization_code ***')
        auth_code = AuthorizationCode.query.filter_by(
            code=code, client_id=client.client_id).first()
        if auth_code and not auth_code.is_expired():
            return auth_code

    def delete_authorization_code(self, authorization_code):
        print('*** authorization_code_grant:delete_authorization_code ***')
        db.session.delete(authorization_code)
        db.session.commit()

    def authenticate_user(self, authorization_code):
        print('*** authorization_code_grant:authenticate_user ***')
        return Account.query.get(authorization_code.account_id)


class PasswordGrant(grants.ResourceOwnerPasswordCredentialsGrant):
    def authenticate_user(self, username, password):
        account = Account.query.filter_by(username=username).first()
        print(account.check_password(password))
        if account is not None and account.check_password(password):
            return account


class RefreshTokenGrant(grants.RefreshTokenGrant):
    def authenticate_refresh_token(self, refresh_token):
        token = Token.query.filter_by(refresh_token=refresh_token).first()
        if token and token.is_refresh_token_active():
            return token

    def authenticate_user(self, credential):
        return Account.query.get(credential.user_id)

    def revoke_old_credential(self, credential):
        credential.revoked = True
        db.session.add(credential)
        db.session.commit()

from .config import Config

config = Config()

class OpenIDCode(oidc_grants.OpenIDCode):
    def exists_nonce(self, nonce, request):
        print('*** openid_code_grant:exists_nonce ***')
        exists = AuthorizationCode.query.filter_by(
            client_id=request.client_id, nonce=nonce
        ).first()
        return bool(exists)

    def get_jwt_config(self, grant):
        print('*** openid_code_grant:get_jwt_config ***')
        return {
            'key': config.get_jwt_key(),
            'alg': 'HS256',
            'iss': config.get_jwt_issuer(),
            'exp': 3600
        }

    def generate_user_info(self, user, scope):
        print('*** openid_code_grant:get_user_info ***')
        user_info = UserInfo(sub=user.id, name=user.username)
        if 'email' in scope:
            user_info['email'] = user.email
        return user_info

class OpenIDImplicitGrant(oidc_grants.OpenIDImplicitGrant):
    def exists_nonce(self, nonce, request):
        print('*** openid_implicit_grant:exists_nonce ***')
        exists = AuthorizationCode.query.filter_by(
            client_id=request.client_id, nonce=nonce
        ).first()
        return bool(exists)

    def get_jwt_config(self):
        print('*** openid_implicit_grant:get_jwt_config ***')
        return {
            'key': config.get_jwt_key(),
            'alg': 'HS256',
            'iss': config.get_jwt_issuer(),
            'exp': 3600
        }

    def generate_user_info(self, user, scope):
        print('*** openid_implicit_grant:generate_user_info ***')
        user_info = UserInfo(sub=user.id, name=user.name)
        if 'email' in scope:
            user_info['email'] = user.email
        return user_info

def create_authorization_code(client, grant_user, request):
    code = gen_salt(48)
    nonce = request.data.get('nonce')
    auth_code = AuthorizationCode(
        code=code,
        client_id=request.client.client_id,
        redirect_uri=request.redirect_uri,
        scope=request.scope,
        user_id=request.user.id,
        nonce=nonce)
    db.session.add(auth_code)
    db.session.commit()
    return code

class HybridGrant(oidc_grants.OpenIDHybridGrant):

    def create_authorization_code(self, client, grant_user, request):
        print('*** hybrid_grant:create_authorization_code ***')
        return create_authorization_code(client, grant_user, request)

    def exists_nonce(self, nonce, request):
        print('*** hybrid_grant:exists_nonce ***')
        exists = AuthorizationCode.query.filter_by(
            client_id=request.client_id, nonce=nonce
        ).first()
        return bool(exists)

    def get_jwt_config(self):
        print('*** hybrid_grant:get_jwt_config ***')
        return {
            'key': config.get_jwt_key(),
            'alg': 'RS512',
            'iss': config.get_jwt_issuer(),
            'exp': 3600
        }

    def generate_user_info(self, user, scope):
        print('*** hybrid_grant:generate_user_info ***')
        user_info = UserInfo(sub=user.id, name=user.name)
        if 'email' in scope:
            user_info['email'] = user.email
        return user_info


query_client = create_query_client_func(db.session, App)
save_token = create_save_token_func(db.session, Token)
authorization = AuthorizationServer(
    query_client=query_client,
    save_token=save_token,
)
require_oauth = ResourceProtector()


def config_oauth(app):
    authorization.init_app(app)

    # support all grants
    authorization.register_grant(grants.ImplicitGrant)
    authorization.register_grant(OpenIDImplicitGrant)
    authorization.register_grant(grants.ClientCredentialsGrant)
    authorization.register_grant(AuthorizationCodeGrant, [CodeChallenge(required=True), OpenIDCode(require_nonce=True)])
    authorization.register_grant(HybridGrant)

    authorization.register_grant(PasswordGrant)
    authorization.register_grant(RefreshTokenGrant)

    # support revocation
    revocation_cls = create_revocation_endpoint(db.session, Token)
    authorization.register_endpoint(revocation_cls)

    # protect resource
    bearer_cls = create_bearer_token_validator(db.session, Token)
    require_oauth.register_token_validator(bearer_cls())