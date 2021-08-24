import enum
import uuid
import time
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
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


class Account(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.Enum(AccountType))
    username = db.Column(db.String(40), unique=True)
    email = db.Column(db.String(254), unique=True)
    password_hash = db.Column(db.String(128))
    data = db.Column(db.JSON)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    home_id = db.Column(db.String(36), db.ForeignKey('item.id'))
    parent_id = db.Column(db.String(36), db.ForeignKey('account.id'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        print(password)
        return check_password_hash(self.password_hash, password)

    def get_user_id(self):
        return self.id

    def __str__(self):
        return self.username


class GroupRoleType(enum.Enum):
    root = 1
    admin = 2
    contributor = 3
    member = 4
    guest = 5


# Define the Group data-model
class Group(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), unique=True)
    parent_id = db.Column(db.String(36), db.ForeignKey('group.id'))


# Define the AccountGroup association table
class AccountGroup(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    account_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    role_type = db.Column(db.Enum(GroupRoleType), nullable=False)
    account = db.relationship('Account')
    group = db.relationship('Group')


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


class VisibilityType(enum.Enum):
    visible = 1
    hidden = 2
    restricted = 3

class Item(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    attributes = db.Column(db.JSON)
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id'), nullable=False)
    type_id = db.Column(db.String(36), db.ForeignKey('type.id'), nullable=False)
    parent_id = db.Column(db.String(36), db.ForeignKey('item.id'))
    location = db.Column(Geometry(geometry_type='GEOMETRY', srid=4326))
    visibility = db.Column(db.Enum(VisibilityType))
    tags = db.Column(db.ARRAY(db.String()))
    type = db.relationship('Type')
    acls = db.relationship('Acl')
    # parent = db.relationship('Item')


class Function(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    code = db.Column(db.Text)
    data = db.Column(db.JSON)
    item_id = db.Column(db.String(36), db.ForeignKey('item.id'), nullable=False)


class Topic(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    data = db.Column(db.JSON)
    item_id = db.Column(db.String(36), db.ForeignKey('item.id'), nullable=False)

class TopicFunction(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    topic_id = db.Column(db.String(36), db.ForeignKey('topic.id'), nullable=False)
    function_id = db.Column(db.String(36), db.ForeignKey('function.id'), nullable=False)
    function = db.relationship('Function')


class Message(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    data = db.Column(db.JSON)
    topic_id = db.Column(db.String(36), db.ForeignKey('topic.id'), nullable=False)

class AclType(enum.Enum):
    public = 1
    group = 2
    user = 3


# Define the Acl data-model
class Acl(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.Enum(AclType))
    name = db.Column(db.String(50))
    permission = db.Column(db.String(50))
    item_id = db.Column(db.String(36), db.ForeignKey('item.id'), nullable=False)


class BlobType(enum.Enum):
    local = 1
    s3 = 2


# Define the Acl data-model
class Blob(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.Enum(BlobType))
    data = db.Column(db.JSON)
    content_length = db.Column(db.Integer, nullable=False)
    content_type = db.Column(db.String(36), nullable=False)
    filename = db.Column(db.String(250), nullable=False)
    mime_type = db.Column(db.String(36), nullable=False)
    item_id = db.Column(db.String(36), db.ForeignKey('item.id'), nullable=False)

def create_account(tenant_name,
                   account_type,
                   account_role,
                   account_username,
                   account_password,
                   account_email):
    id = str(uuid.uuid4())
    group = db.session.query(Group).filter(Group.name == tenant_name).first()
    if not group:
        return None
    account = Account(id=id,
                           type=AccountType[account_type],
                           username=account_username,
                           email=account_email,
                           group_id=group.id)
    account.set_password(account_password)

    db.session.add(account)

    db.session.add(AccountGroup(id=str(uuid.uuid4()),
                                account_id=account.id,
                                group_id=group.id,
                                role_type=GroupRoleType[account_role]))
    folder_type = db.session.query(Type).filter(Type.name == 'Folder').first()
    if not folder_type:
        return None

    person_type = db.session.query(Type).filter(Type.name == 'Person').first()
    if not person_type:
        return None

    db.session.add(Item(id=account.id,
                        name=account.username,
                        owner_id=account.id,
                        group_id=group.id,
                        type_id=person_type.id))

    home_folder_id = str(uuid.uuid4())
    db.session.add(Item(id=home_folder_id,
                        name='Home',
                        owner_id=account.id,
                        group_id=group.id,
                        type_id=folder_type.id))
    db.session.commit()

    adm = db.session.query(Account).filter(Account.id == account.id).first()
    if adm:
        print('setting user home folder id')
        adm.home_id = home_folder_id

    db.session.commit()

    return account


def add_account(tenant_name, account_username):
    pass

def create_tenant(tenant_name, root_username, root_email, root_password):
    
    root_group_id = str(uuid.uuid4())
    db.session.add(Group(id=root_group_id, name=tenant_name))

    db.session.commit()

    root_account_id = str(uuid.uuid4())
    root_account = Account( id=root_account_id, 
                            type=AccountType.person, 
                            username=root_username, 
                            email=root_email, 
                            group_id=root_group_id)
    root_account.set_password(root_password)

    db.session.add(root_account)

    db.session.add(AccountGroup(id=str(uuid.uuid4()), 
                                account_id=root_account_id, 
                                group_id=root_group_id,
                                role_type=GroupRoleType.root))

    client_id = gen_salt(24)
    client_id_issued_at = int(time.time())
    root_app_id = str(uuid.uuid4())
    client = App(
        id=root_app_id,
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        owner_id=root_account_id,
        group_id=root_group_id
    )

    client_metadata = {
        'client_name': 'root',
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

    print('{} tenant client id: {}'.format(tenant_name, client_id))
    print('{} tenant client secret: {}'.format(tenant_name, client.client_secret))

    # create basic types
    person_type_id = str(uuid.uuid4())
    db.session.add(Type(id=person_type_id, name='Person', owner_id=root_account_id, group_id=root_group_id, module='person'))

    folder_type_id = str(uuid.uuid4())
    db.session.add(Type(id=folder_type_id, name='Folder', owner_id=root_account_id, group_id=root_group_id))

    db.session.add(Item(id=root_account_id, 
                        name=root_username, 
                        owner_id=root_account_id, 
                        group_id=root_group_id, 
                        type_id=person_type_id))

    home_folder_id = str(uuid.uuid4())
    db.session.add(Item(id=home_folder_id, 
                        name='Home', 
                        owner_id=root_account_id, 
                        group_id=root_group_id, 
                        type_id=folder_type_id))
    db.session.commit()

    adm = db.session.query(Account).filter(Account.id == root_account_id).first()
    if adm:
        print('setting admin home folder id')
        adm.home_id = home_folder_id

    db.session.commit()

def initialize_server(root_tenant_name,
               root_username,
               root_email, 
               root_password):
    create_tenant(root_tenant_name, root_username, root_email, root_password)
    

    

