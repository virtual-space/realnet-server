import enum
import uuid
import time
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape
from werkzeug.security import generate_password_hash, check_password_hash, gen_salt
from sqlalchemy_serializer import SerializerMixin
import shapely
import json


from authlib.integrations.sqla_oauth2 import (
    OAuth2ClientMixin,
    OAuth2AuthorizationCodeMixin,
    OAuth2TokenMixin,
)

db = SQLAlchemy()

# https://stackoverflow.com/questions/52723239/spatialite-backend-for-geoalchemy2-in-python
# https://flask-sqlalchemy.palletsprojects.com/en/2.x/queries/


class Authenticator(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(40))
    api_base_url = db.Column(db.String(128))
    request_token_url = db.Column(db.String(128))
    access_token_url = db.Column(db.String(128))
    authorize_url = db.Column(db.String(128))
    client_kwargs = db.Column(db.JSON())
    client_id = db.Column(db.String(255))
    client_secret = db.Column(db.String(255))
    userinfo_endpoint = db.Column(db.String(128))
    server_metadata_url = db.Column(db.String(128))
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)


class AccountType(enum.Enum):
    person = 1
    thing = 2


class Account(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.Enum(AccountType))
    username = db.Column(db.String(40))
    email = db.Column(db.String(254))
    password_hash = db.Column(db.String(128))
    data = db.Column(db.JSON)
    external_id = db.Column(db.String(254))
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


class App(db.Model, OAuth2ClientMixin, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(42))
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id'), nullable=False)
    data = db.Column(db.JSON)

    def get_allowed_scope(self, scope):
        if not scope:
            return ''
        allowed = set(self.scope)
        scopes = [s for s in self.scope]
        return ' '.join([s for s in scopes if s in allowed])


class Type(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    icon = db.Column(db.String(128))
    attributes = db.Column(db.JSON)
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id'), nullable=False)
    module = db.Column(db.String(128))

class TypeId:
    person = 'b533fc2f-fcec-46d4-b3ff-5e8589a18ccb'
    folder = '962587e1-9900-435f-a7df-16c10e5f584a'

class VisibilityType(enum.Enum):
    visible = 1
    hidden = 2
    restricted = 3

def jsonize_geometry(g):
    return json.loads(json.dumps(shapely.geometry.mapping(to_shape(g))))

class Item(db.Model, SerializerMixin):
    serialize_types = (
        (WKBElement, lambda x: jsonize_geometry(x)),
    )
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

    if account.type == AccountType.person:
        person_type = db.session.query(Type).filter(Type.name == 'Person').first()
        if not person_type:
            return None

        db.session.add(Item(id=account.id,
                            name=account.username,
                            owner_id=account.id,
                            group_id=group.id,
                            type_id=person_type.id))
    else:
        thing_type = db.session.query(Type).filter(Type.name == 'Thing').first()
        if not thing_type:
            return None

        db.session.add(Item(id=account.id,
                            name=account.username,
                            owner_id=account.id,
                            group_id=group.id,
                            type_id=thing_type.id))

    app_type = db.session.query(Type).filter(Type.name == 'App').first()
    if not app_type:
        return None

    home_folder_id = str(uuid.uuid4())
    db.session.add(Item(id=home_folder_id,
                        name='home',
                        parent_id=account.id,
                        owner_id=account.id,
                        group_id=group.id,
                        type_id=folder_type.id))

    db.session.add(Item(id=uuid.uuid4(),
                        name='Find',
                        attributes={'views': [{'name': 'Items', 'type': 'List', 'icon': 'view_list'}], 'query': {}},
                        parent_id=account.id,
                        owner_id=account.id,
                        group_id=group.id,
                        type_id=app_type.id))

    db.session.add(Item(id=uuid.uuid4(),
                        name='Around',
                        attributes={'views': [{'name': 'Items', 'type': 'List', 'icon': 'view_list'}], 'query': {}},
                        parent_id=account.id,
                        owner_id=account.id,
                        group_id=group.id,
                        type_id=app_type.id))

    db.session.add(Item(id=uuid.uuid4(),
                        name='Home',
                        attributes={'views': [{'name': 'Items', 'type': 'List', 'icon': 'view_list'}], 'query': {}},
                        parent_id=account.id,
                        owner_id=account.id,
                        group_id=group.id,
                        type_id=app_type.id))

    db.session.commit()

    adm = db.session.query(Account).filter(Account.id == account.id).first()
    if adm:
        print('setting user home folder id')
        adm.home_id = home_folder_id

    db.session.commit()

    return account

def get_or_create_delegated_account(tenant_name,
                                    account_type,
                                    account_role,
                                    account_username,
                                    account_email,
                                    account_external_id):
    id = str(uuid.uuid4())
    group = db.session.query(Group).filter(Group.name == tenant_name).first()
    if not group:
        return None

    account = db.session.query(Account).filter(Account.external_id == account_external_id, Account.group_id == group.id).first()

    if account:
        return account

    account = Account(id=id,
                          type=AccountType[account_type],
                          username=account_username,
                          external_id=account_external_id,
                          email=account_email,
                          group_id=group.id)

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

    app_type = db.session.query(Type).filter(Type.name == 'App').first()
    if not app_type:
        return None

    db.session.add(Item(id=account.id,
                        name=account.username,
                        owner_id=account.id,
                        group_id=group.id,
                        type_id=person_type.id))

    home_folder_id = str(uuid.uuid4())

    db.session.add(Item(id=home_folder_id,
                        name='home',
                        owner_id=account.id,
                        parent_id=account.id,
                        group_id=group.id,
                        type_id=folder_type.id))
    db.session.add(Item(id=uuid.uuid4(),
                        name='Find',
                        attributes={'views': [{'name': 'Items', 'type': 'List', 'icon': 'view_list'}], 'query': {}},
                        parent_id=account.id,
                        owner_id=account.id,
                        group_id=group.id,
                        type_id=app_type.id))

    db.session.add(Item(id=uuid.uuid4(),
                        name='Around',
                        attributes={'views': [{'name': 'Items', 'type': 'List', 'icon': 'view_list'}], 'query': {}},
                        parent_id=account.id,
                        owner_id=account.id,
                        group_id=group.id,
                        type_id=app_type.id))

    db.session.add(Item(id=uuid.uuid4(),
                        name='Home',
                        attributes={'views': [{'name': 'Items', 'type': 'List', 'icon': 'view_list'}], 'query': {}},
                        parent_id=account.id,
                        owner_id=account.id,
                        group_id=group.id,
                        type_id=app_type.id))
    db.session.commit()

    adm = db.session.query(Account).filter(Account.id == account.id).first()
    if adm:
        print('setting user home folder id')
        adm.home_id = home_folder_id

    db.session.commit()

    return account

def create_app(name,
               uri,
               grant_types,
               redirect_uris,
               response_types,
               scope,
               auth_method,
               account_id,
               group_id,
               client_id=gen_salt(24)
               ):
    client_id_issued_at = int(time.time())
    app_id = str(uuid.uuid4())
    client = App(
        id=app_id,
        name=name,
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        owner_id=account_id,
        group_id=group_id
    )

    client_metadata = {
        'client_name': name,
        'client_uri': uri,
        'grant_types': grant_types,
        'redirect_uris': redirect_uris,
        'response_types': response_types,
        'scope': scope,
        'token_endpoint_auth_method': auth_method
    }
    client.set_client_metadata(client_metadata)

    if client_metadata['token_endpoint_auth_method'] == 'none':
        client.client_secret = ''
    else:
        client.client_secret = gen_salt(48)

    db.session.add(client)
    db.session.commit()

    return client

def create_tenant(tenant_name, root_username, root_email, root_password, uri, web_redirect_uri):
    
    root_group_id = str(uuid.uuid4())
    root_group = Group(id=root_group_id, name=tenant_name)
    db.session.add(root_group)

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

    cli_client = create_app(name=tenant_name + '_cli',
                        client_id='Vk6Swe7GyqJIKKfa3SiXYJbv',
                        uri=uri,
                        grant_types=['password'],
                        redirect_uris=[],
                        response_types=['token'],
                        scope='',
                        auth_method='client_secret_basic',
                        account_id=root_account_id,
                        group_id=root_group_id)

    web_client = create_app(name=tenant_name + '_web',
                        client_id='IEmf5XYQJXIHvWcQtZ5FXbLM',
                        uri=uri,
                        grant_types=['password'],
                        redirect_uris=[web_redirect_uri],
                        response_types=['token'],
                        scope='',
                        auth_method='none',
                        account_id=root_account_id,
                        group_id=root_group_id)

    print('{} tenant id: {}'.format(tenant_name, root_group_id))
    print('{} tenant cli client id: {}'.format(tenant_name, cli_client.client_id))
    print('{} tenant cli client secret: {}'.format(tenant_name, cli_client.client_secret))
    print('{} tenant web client id: {}'.format(tenant_name, web_client.client_id))
    print('{} tenant root id: {}'.format(tenant_name, root_account_id))
    print('{} tenant root email: {}'.format(tenant_name, root_email))
    print('{} tenant root username: {}'.format(tenant_name, root_username))
    print('{} tenant root password: {}'.format(tenant_name, root_password))

    create_basic_types(root_account_id, root_group_id)

    folder_type = db.session.query(Type).filter(Type.name == 'Folder').first()
    if not folder_type:
        return None

    person_type = db.session.query(Type).filter(Type.name == 'Person').first()
    if not person_type:
        return None

    app_type = db.session.query(Type).filter(Type.name == 'App').first()
    if not app_type:
        return None


    db.session.add(Item(id=root_account_id, 
                        name=root_username, 
                        owner_id=root_account_id, 
                        group_id=root_group_id, 
                        type_id=person_type.id))

    home_folder_id = str(uuid.uuid4())
    db.session.add(Item(id=home_folder_id, 
                        name='home',
                        parent_id=root_account_id,
                        owner_id=root_account_id, 
                        group_id=root_group_id, 
                        type_id=folder_type.id))

    db.session.add(Item(id=uuid.uuid4(),
                        name='Find',
                        attributes={'views': [{'name': 'Items', 'type': 'List', 'icon': 'view_list'}], 'query': {}},
                        parent_id=root_account_id,
                        owner_id=root_account_id,
                        group_id=root_group_id,
                        type_id=app_type.id))

    db.session.add(Item(id=uuid.uuid4(),
                        name='Around',
                        attributes={'views': [{'name': 'Items', 'type': 'List', 'icon': 'view_list'}], 'query': {}},
                        parent_id=root_account_id,
                        owner_id=root_account_id,
                        group_id=root_group_id,
                        type_id=app_type.id))

    db.session.add(Item(id=uuid.uuid4(),
                        name='Home',
                        attributes={'views': [{'name': 'Items', 'type': 'List', 'icon': 'view_list'}], 'query': {}},
                        parent_id=root_account_id,
                        owner_id=root_account_id,
                        group_id=root_group_id,
                        type_id=app_type.id))

    db.session.commit()
    print('{} tenant root home folder id: {}'.format(tenant_name, home_folder_id))
    adm = db.session.query(Account).filter(Account.id == root_account_id).first()
    if adm:
        print('setting admin home folder id')
        adm.home_id = home_folder_id

    db.session.commit()

    create_basic_types(root_account_id, root_group_id)
    result = root_group.to_dict()
    result['client_id'] = cli_client.client_id
    result['client_secret'] = cli_client.client_secret
    result['root_username'] = root_username
    result['root_password'] = root_password
    result['root_email'] = root_email
    return result

def get_or_create_type(name, icon, owner_id, group_id, module=None):
    res = db.session.query(Type).filter(Type.name == name).first()

    if not res:
        res = Type(id=str(uuid.uuid4()), name=name, icon=icon, owner_id=owner_id, group_id=group_id, module=module)
        db.session.add(res)
        db.session.commit()

    return res

def create_basic_types(owner_id, group_id):
    get_or_create_type(name='Person', owner_id=owner_id, group_id=group_id, module='person', icon='person')
    get_or_create_type(name='Thing', owner_id=owner_id, group_id=group_id, icon='graphic_eq')

    get_or_create_type(name='Folder', owner_id=owner_id, group_id=group_id, icon='folder')
    get_or_create_type(name='Document', owner_id=owner_id, group_id=group_id, icon='description')
    get_or_create_type(name='Image', owner_id=owner_id, group_id=group_id, icon='image')
    get_or_create_type(name='Video', owner_id=owner_id, group_id=group_id, icon='ondemand_video')
    get_or_create_type(name='Drawing', owner_id=owner_id, group_id=group_id, icon='gesture')
    get_or_create_type(name='Scene', owner_id=owner_id, group_id=group_id, icon='view_in_ar')

    get_or_create_type(name='App', owner_id=owner_id, group_id=group_id, icon='apps')

    get_or_create_type(name='Place', owner_id=owner_id, group_id=group_id, icon='other_houses')
    get_or_create_type(name='Event', owner_id=owner_id, group_id=group_id, icon='event')
    get_or_create_type(name='Task', owner_id=owner_id, group_id=group_id, icon='assignment_turned_in')
    get_or_create_type(name='Job', owner_id=owner_id, group_id=group_id, icon='trending_up')

def initialize_server(root_tenant_name,
               root_username,
               root_email, 
               root_password,
               uri,
               web_redirect_uri):
    create_tenant(root_tenant_name, root_username, root_email, root_password, uri, web_redirect_uri)

    

    

