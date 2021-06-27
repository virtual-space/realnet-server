import enum
import uuid
import time
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash, gen_salt
from sqlalchemy_serializer import SerializerMixin

from authlib.integrations.sqla_oauth2 import (
    OAuth2ClientMixin,
    OAuth2AuthorizationCodeMixin,
    OAuth2TokenMixin,
)


class AuthenticatorType(enum.Enum):
    password = 1
    oauth = 2


db = SQLAlchemy()

# https://stackoverflow.com/questions/52723239/spatialite-backend-for-geoalchemy2-in-python
# https://flask-sqlalchemy.palletsprojects.com/en/2.x/queries/

class Authenticator(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(40))
    type = db.Column(db.Enum(AuthenticatorType))
    client_id = db.Column(db.String(128))
    client_secret = db.Column(db.String(128))

class AccountType(enum.Enum):
    person = 1
    thing = 2

class Account(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.Enum(AccountType))
    username = db.Column(db.String(40), unique=True)
    email = db.Column(db.String(254), unique=True)
    password_hash = db.Column(db.String(128))
    data = db.Column(db.JSON)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    home_id = db.Column(db.String(36), db.ForeignKey('item.id'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def get_user_id(self):
        return self.id

    def __str__(self):
        return self.username

# Define the Role data-model
class Role(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), unique=True)

# Define the AccountRole association table
class AccountRole(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    account_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    role_id = db.Column(db.String(36), db.ForeignKey('role.id', ondelete='CASCADE'), nullable=False)


# Define the Group data-model
class Group(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), unique=True)

# Define the AccountGroup association table
class AccountGroup(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    account_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)


class Token(db.Model, OAuth2TokenMixin):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')

class AuthorizationCode(db.Model, OAuth2AuthorizationCodeMixin):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')

class App(db.Model, OAuth2ClientMixin):
    id = db.Column(db.String(36), primary_key=True)
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id'), nullable=False)
    data = db.Column(db.JSON)

class Type(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    attributes = db.Column(db.JSON)
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id'), nullable=False)
    module = db.Column(db.String(128))

class Item(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    attributes = db.Column(db.JSON)
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id'), nullable=False)
    type_id = db.Column(db.String(36), db.ForeignKey('type.id'), nullable=False)
    parent_id = db.Column(db.String(36), db.ForeignKey('item.id'))
    type = db.relationship('Type')
    acls = db.relationship('Acl')
    # parent = db.relationship('Item')

class AclType(enum.Enum):
    public = 1
    group = 2
    user = 3

# Define the Acl data-model
class Acl(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.Enum(AclType))
    name = db.Column(db.String(50))
    permission = db.Column(db.String(50))
    item_id = db.Column(db.String(36), db.ForeignKey('item.id'), nullable=False)


def initialize():
    # db.session.add(Authenticator(id=str(uuid.uuid4()), name='realnet', type=AuthenticatorType.password))
    # create admin account
    admin_role_id = str(uuid.uuid4())
    db.session.add(Role(id=admin_role_id, name='admin'))

    group_id = str(uuid.uuid4())
    db.session.add(Group(id=group_id, name='admin'))

    account_id = str(uuid.uuid4())
    account = Account(id=account_id, type=AccountType.person, username='admin', email='admin@realnet.io', group_id=group_id)
    account.set_password('123456')
    db.session.add(account)

    db.session.add(AccountRole(id=str(uuid.uuid4()), account_id=account_id, role_id=admin_role_id))

    # create basic types
    person_type_id = str(uuid.uuid4())
    db.session.add(Type(id=person_type_id, name='Person', owner_id=account_id, group_id=group_id, module='person'))
    folder_type_id = str(uuid.uuid4())
    db.session.add(Type(id=folder_type_id, name='Folder', owner_id=account_id, group_id=group_id))
    fs_type_id = str(uuid.uuid4())
    db.session.add(Type(id=fs_type_id, name='Filesystem', owner_id=account_id, group_id=group_id, module='filesystem'))

    db.session.add(Item(id=account_id, name='Admin', owner_id=account_id, group_id=group_id, type_id=person_type_id))

    home_folder_id = str(uuid.uuid4())
    db.session.add(Item(id=home_folder_id, name='Home', owner_id=account_id, group_id=group_id, type_id=folder_type_id))
    db.session.commit()

    adm = db.session.query(Account).filter(Account.id == account_id).first()
    if adm:
        print('setting admin home folder id')
        adm.home_id = home_folder_id

    db.session.add(Item(id=str(uuid.uuid4()),
                        name='My filesystem',
                        owner_id=account_id,
                        group_id=group_id,
                        type_id=fs_type_id,
                        parent_id=home_folder_id,
                        attributes={'path': '.'}))
    db.session.commit()

    client_id = gen_salt(24)
    client_id_issued_at = int(time.time())
    client = App(
        id=str(uuid.uuid4()),
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        owner_id=account_id,
        group_id=group_id
    )

    client_metadata = {
        'client_name': 'realnet',
        'client_uri': 'http://localhost:8080',
        'grant_types': ['authorization_code', 'password'],
        'redirect_uris': [],
        'response_types': ['code'],
        'scope': '',
        'token_endpoint_auth_method': 'client_secret_basic'
    }
    client.set_client_metadata(client_metadata)

    if client_metadata['token_endpoint_auth_method'] == 'none':
        client.client_secret = ''
    else:
        client.client_secret = gen_salt(48)

    db.session.add(client)
    db.session.commit()

