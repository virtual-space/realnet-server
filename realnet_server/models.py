import enum
from unicodedata import name
import uuid
import time
import os
import sys
from flask_sqlalchemy import SQLAlchemy
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement
from geoalchemy2.shape import to_shape
from werkzeug.security import generate_password_hash, check_password_hash, gen_salt
from sqlalchemy_serializer import SerializerMixin
import shapely
import json
import csv

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
    user_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    account = db.relationship('Account')


class AuthorizationCode(db.Model, OAuth2AuthorizationCodeMixin):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    account = db.relationship('Account')


class App(db.Model, OAuth2ClientMixin, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(42))
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
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
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    base_id = db.Column(db.String(36), db.ForeignKey('type.id', ondelete='CASCADE'))
    module = db.Column(db.String(128))
    base = db.relationship('Type')
    instances = db.relationship('Instance', foreign_keys='[Instance.parent_type_id]')

class VisibilityType(enum.Enum):
    visible = 1
    hidden = 2
    restricted = 3

class Instance(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    icon = db.Column(db.String(128))
    attributes = db.Column(db.JSON)
    public = db.Column(db.Boolean)
    visibility = db.Column(db.Enum(VisibilityType))
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    type_id = db.Column(db.String(36), db.ForeignKey('type.id', ondelete='CASCADE'), nullable=False)
    type = db.relationship('Type', foreign_keys='[Instance.type_id]')
    parent_type_id = db.Column(db.String(36), db.ForeignKey('type.id'))

class TypeId:
    person = 'b533fc2f-fcec-46d4-b3ff-5e8589a18ccb'
    folder = '962587e1-9900-435f-a7df-16c10e5f584a'



def jsonize_geometry(g):
    return json.loads(json.dumps(shapely.geometry.mapping(to_shape(g))))

class Item(db.Model, SerializerMixin):
    serialize_types = (
        (WKBElement, lambda x: jsonize_geometry(x)),
    )
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    attributes = db.Column(db.JSON)
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)
    type_id = db.Column(db.String(36), db.ForeignKey('type.id', ondelete='CASCADE'), nullable=False)
    parent_id = db.Column(db.String(36), db.ForeignKey('item.id'))
    location = db.Column(Geometry(geometry_type='GEOMETRY', srid=4326))
    visibility = db.Column(db.Enum(VisibilityType))
    tags = db.Column(db.ARRAY(db.String()))
    type = db.relationship('Type')
    acls = db.relationship('Acl', passive_deletes=True)
    # parent = db.relationship('Item')


class Function(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    code = db.Column(db.Text)
    data = db.Column(db.JSON)
    item_id = db.Column(db.String(36), db.ForeignKey('item.id', ondelete='CASCADE'), nullable=False)


class Topic(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    data = db.Column(db.JSON)
    item_id = db.Column(db.String(36), db.ForeignKey('item.id', ondelete='CASCADE'), nullable=False)

class TopicFunction(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    topic_id = db.Column(db.String(36), db.ForeignKey('topic.id', ondelete='CASCADE'), nullable=False)
    function_id = db.Column(db.String(36), db.ForeignKey('function.id', ondelete='CASCADE'), nullable=False)
    function = db.relationship('Function')


class Message(db.Model, SerializerMixin):
    id = db.Column(db.String(36), primary_key=True)
    data = db.Column(db.JSON)
    topic_id = db.Column(db.String(36), db.ForeignKey('topic.id', ondelete='CASCADE'), nullable=False)

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
    item_id = db.Column(db.String(36), db.ForeignKey('item.id', ondelete='CASCADE'), nullable=False)


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
    item_id = db.Column(db.String(36), db.ForeignKey('item.id', ondelete='CASCADE'), nullable=False)

def traverse_instance(instances, instance, parent_type_name):
    for inst in instance.get('instances', []):
        instances.append({ "instance": inst, "parent_type_name": parent_type_name})
        traverse_instance(instances, inst, inst.get('type'))

def build_item( instance,
                attributes,
                item_data,
                owner_id,
                group_id,
                parent_item_id=None):

    item = Item( id=instance.id,
                 name=instance.name,
                 attributes=attributes,
                 owner_id=owner_id,
                 group_id=group_id,
                 type_id=instance.type.id,
                 parent_id=parent_item_id)
    
    db.session.add(item)
    db.session.commit()

    create_public_acl = instance.public

    if item_data and 'item_is_public' in item_data:
        if item_data['item_is_public'] == 'true':
            create_public_acl = True

    if create_public_acl:
        acl = Acl(id=str(uuid.uuid4()),type=AclType.public,item_id=instance.id)
        db.session.add(acl)
        db.session.commit()
    
    for child_instance in instance.type.instances:
        attributes = child_instance.type.attributes
        if attributes:
            if child_instance.attributes:
                attributes =  attributes | child_instance.attributes
        elif child_instance.attributes:
            attributes = child_instance.attributes
        
        child_item = build_item(  child_instance,
                                  attributes,
                                  {},
                                  owner_id,
                                  group_id,
                                  item.id)

    return item

def create_item(db,
                item_id,
                item_type_name, 
                item_name,
                item_attributes,
                item_location,
                item_visibility,
                item_tags,
                item_is_public,
                owner_id,
                group_id,
                parent_item_id=None):

    item = None
    item_type = Type.query.filter(Type.name == item_type_name).first()
    if not item_type:
        item_type = Type(id=str(uuid.uuid4()),
                         name=item_type_name,
                         owner_id=owner_id,
                         group_id=group_id)
        db.session.add(item_type)
        db.session.commit()

    if item_type:
        # attributes = item_attributes | item_type.attributes
        attributes = item_type.attributes
        if attributes:
            if item_attributes:
                attributes =  attributes | item_attributes
        elif item_attributes:
            attributes = item_attributes 

        instance = Instance(id=item_id,
                            name=item_name,
                            public=item_is_public == "true",
                            owner_id=owner_id,
                            group_id=group_id,
                            type_id=item_type.id)

        db.session.add(instance)
        db.session.commit()

        item_data = {"item_location": item_location, 
                     "item_visibility": item_visibility,
                     "item_tags": item_tags,
                     "item_is_public": item_is_public}
        
        item = build_item(instance, attributes, item_data, owner_id, group_id, parent_item_id)
    
    return item

def import_types(db, type_data, owner_id, group_id):
    types = dict()
    instances = []
    commit_needed = False
    for td in type_data['types']:
        existing_type = Type.query.filter(Type.name == td['name']).first()
        if not existing_type:
            base_id = None
            base_name = td.get('base')
            if base_name:
                base_type = Type.query.filter(Type.name == base_name).first()
                if base_type:
                    base_id = base_type.id
            attributes = td.get('attributes', dict())
            existing_type = Type(id=str(uuid.uuid4()),
                                        name=td['name'],
                                        icon=attributes.get('icon'),
                                        attributes=td.get('attributes'),
                                        owner_id=owner_id,
                                        group_id=group_id,
                                        module=td.get('module'),
                                        base_id=base_id)
            for instance in td.get('instances', []):
                instances.append({ "instance": instance, "parent_type_name": existing_type.name})
            db.session.add(existing_type)     
            commit_needed = True                       
        
        types[existing_type.name] = {"type": existing_type, "instances": td.get('instances', []) }

    for td in type_data['types']:
        existing_type = Type.query.filter(Type.name == td['name']).first()
        base = td.get('base')
        if not existing_type and base:
            attributes = td.get('attributes', dict())
            existing_type = Type(id=str(uuid.uuid4()),
                                        name=td['name'],
                                        icon=attributes.get('icon'),
                                        attributes=td.get('attributes'),
                                        owner_id=owner_id,
                                        group_id=group_id,
                                        base_id=types[base]['type']['id'],
                                        module=td.get('module'))
            for instance in td.get('instances', []):
                instances.append({ "instance": instance, "parent_type_name": existing_type.name})
            db.session.add(existing_type)     
            commit_needed = True                       
        
        types[existing_type.name] = {"type": existing_type, "instances": td.get('instances', []) }
    
    if commit_needed:
        db.session.commit()
        commit_needed = False
    
    subinstances = []

    for ie in instances:
        instance = ie['instance']
        parent_type_name = ie['parent_type_name']
        traverse_instance(subinstances, instance, parent_type_name)

    instances.extend(subinstances)    

    for ie in instances:
        instance = ie['instance']
        parent_type_name = ie['parent_type_name']
        target = types.get(instance['type'], Type.query.filter(Type.name == instance['type']).first())
        if target:
            parent = types.get(parent_type_name, Type.query.filter(Type.name == parent_type_name).first())
            attributes = instance.get('attributes', dict())
            is_public = instance.get('public')
            if is_public:
                is_public = is_public.lower() in ['true', 'True', '1']
            
            created_instance = Instance(id=str(uuid.uuid4()),
                                        name=instance['name'],
                                        icon=attributes.get('icon'),
                                        attributes=instance.get('attributes'),
                                        public=is_public,
                                        owner_id=owner_id,
                                        group_id=group_id,
                                        type_id=target['type'].id,
                                        parent_type_id=parent['type'].id)
            db.session.add(created_instance)
            commit_needed = True
            
    
    if commit_needed:
        db.session.commit()

    return [dv['type'].to_dict() for dv in types.values()]


def traverse_item(db, item_ids, items_by_id, children_by_id, item, owner_id, group_id):
    parent_id = item.get('parent_id')
    if parent_id:
        create_item(db, 
                        item_ids[item['id']], 
                        item['type'], 
                        item['name'],
                        item.get('attributes'),
                        item.get('location'),
                        item.get('visibility'),
                        item.get('tags'),
                        item.get('public'),
                        owner_id,
                        group_id,
                        item_ids[parent_id])
    else:
        create_item(db, 
                    item_ids[item['id']], 
                    item['type'], 
                    item['name'],
                    item.get('attributes'),
                    item.get('location'),
                    item.get('visibility'),
                    item.get('tags'),
                    item.get('public'),
                    owner_id,
                    group_id)
    for child in children_by_id.get(item['id'], []):
        traverse_item(db, item_ids, items_by_id, children_by_id, items_by_id.get(child), owner_id, group_id)

def import_items(db, items, owner_id, group_id):
    items_by_id = dict()
    root_items = []
    children_by_id = dict()
    item_ids = dict()
    all_items = []

    for item in items:
        item_attributes = dict()
        item_parent_id = item[0]
        item_id = item[1]
        item_type = item[2]
        item_name = item[3]
        item_is_public = item[4]
        item_visibility = item[5]
        item_location = item[6]
        item_tags = item[7]
        
        for av in item[8:]:
            kv = av.split(':')
            if kv and len(kv) > 1:
                item_attributes[kv[0]] = kv[1]
        item_data = dict()

        if item_parent_id == item_id:
            item_data = {"id": item_id,
                        "type": item_type,
                        "attributes": item_attributes,
                        "name": item_name,
                        "location": item_location,
                        "visibility": item_visibility,
                        "tags": item_tags,
                        "public": item_is_public}
        else:
            item_data = {"id": item_id,
                        "type": item_type,
                        "attributes": item_attributes,
                        "name": item_name,
                        "location": item_location,
                        "visibility": item_visibility,
                        "tags": item_tags,
                        "parent_id": item_parent_id,
                        "public": item_is_public}
        item_ids[item_id] = str(uuid.uuid4())

        if item_parent_id:
            if item_parent_id == item_id:
                root_items.append(item_data)
            else:
                existingChildren = children_by_id.get(item_parent_id)
                if not existingChildren:
                    existingChildren = [item_id]
                    children_by_id[item_parent_id] = existingChildren
                else:
                    existingChildren.append(item_id)
        items_by_id[item_id] = item_data
        all_items.append(item_data)

    for item in root_items:
        traverse_item(db, item_ids, items_by_id, children_by_id, item, owner_id, group_id)

def import_items_from_file(db, file):
    pass

def create_basic_types(owner_id, group_id):
    with open(os.path.join(os.path.dirname(sys.modules[__name__].__file__),
                           "resources/types.json"), 'r') as f:
        data = json.load(f)
        if data:
            type_data = data.get('types')
            if type_data:
                import_types(db, data,owner_id, group_id)

def create_basic_items(owner_id, group_id):
    with open(os.path.join(os.path.dirname(sys.modules[__name__].__file__),
                           "resources/items.csv"), 'r') as f:
        items = []
        for row in csv.reader(f, dialect=csv.excel):
            if row:
                items.append(row)
        if items:
            results = import_items(db, items, owner_id, group_id)


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

    group = AccountGroup(id=str(uuid.uuid4()),
                                account_id=account.id,
                                group_id=group.id,
                                role_type=GroupRoleType[account_role])
    db.session.add(group)

    db.session.commit()

    create_account_dt(account, group)

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

    group = AccountGroup(id=str(uuid.uuid4()),
                                account_id=account.id,
                                group_id=group.id,
                                role_type=GroupRoleType[account_role])
    db.session.add(group)

    db.session.commit()

    create_account_dt(account, group)
    
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
               client_id=gen_salt(24),
               client_secret=gen_salt(48)
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
        client.client_secret = client_secret

    db.session.add(client)
    db.session.commit()

    return client

def create_account_dt(db, account, group):
    item = None
    if account.type == AccountType.person:
        person_type = db.session.query(Type).filter(Type.name == 'Person').first()
        if not person_type:
            return None
        item = create_item(db,
                            item_type_name=person_type.name,
                            item_id=account.id,
                            item_name=account.username,
                            item_attributes=dict(),
                            item_location=None,
                            item_visibility=None,
                            item_tags=None,
                            item_is_public=None,
                            owner_id=account.id,
                            group_id=group.id
                            )
        db.session.add(item)
        db.session.commit()
    else:
        thing_type = db.session.query(Type).filter(Type.name == 'Thing').first()
        if not thing_type:
            return None
        item = create_item(db,
                            item_type_name=thing_type.name,
                            item_id=account.id,
                            item_name=account.username,
                            item_attributes=dict(),
                            item_location=None,
                            item_visibility=None,
                            item_tags=None,
                            item_is_public=None,
                            owner_id=account.id,
                            group_id=group.id)
        db.session.add(item)
        db.session.commit()
    return item

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

    web_client = create_app(name=tenant_name + '_realscape_web',
                        client_id='IEmf5XYQJXIHvWcQtZ5FXbLM',
                        uri=uri,
                        grant_types=['password'],
                        redirect_uris=[web_redirect_uri],
                        response_types=['token'],
                        scope='',
                        auth_method='none',
                        account_id=root_account_id,
                        group_id=root_group_id)

    mobile_client = create_app(name=tenant_name + '_realscape_mob',
                            client_id='MPpG679mTwfpkwzVfK1flaPa',
                            client_secret='2CNYMgCEVoOsqgSQGipwDN5bo8AsxQktU1KegT7jrQl3Arjq',
                            uri=uri,
                            grant_types=['authorization_code','password'],
                            redirect_uris=["io.realnet.api-dev:/callback"],
                            response_types=['code'],
                            scope='',
                            auth_method='client_secret_basic',
                            account_id=root_account_id,
                            group_id=root_group_id)

    print('{} tenant id: {}'.format(tenant_name, root_group_id))
    print('{} tenant cli client id: {}'.format(tenant_name, cli_client.client_id))
    print('{} tenant cli client secret: {}'.format(tenant_name, cli_client.client_secret))
    print('{} tenant web client id: {}'.format(tenant_name, web_client.client_id))
    print('{} tenant mob client id: {}'.format(tenant_name, mobile_client.client_id))
    print('{} tenant mob client secret: {}'.format(tenant_name, mobile_client.client_secret))
    print('{} tenant root id: {}'.format(tenant_name, root_account_id))
    print('{} tenant root email: {}'.format(tenant_name, root_email))
    print('{} tenant root username: {}'.format(tenant_name, root_username))
    print('{} tenant root password: {}'.format(tenant_name, root_password))

    create_basic_types(root_account_id, root_group_id)
    create_basic_items(root_account_id, root_group_id)
    account_dt = create_account_dt(db, root_account, root_group)

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

def initialize_server(root_tenant_name,
               root_username,
               root_email, 
               root_password,
               uri,
               web_redirect_uri):
    create_tenant(root_tenant_name, root_username, root_email, root_password, uri, web_redirect_uri)

    

    

