from email.mime import base
import uuid
import os
import json

from sqlalchemy import false, null, func

from sqlalchemy.sql import func, and_, or_, not_, functions
try:
    from urllib.parse import unquote  # PY3
except ImportError:
    from urllib import unquote  # PY2

import realnet_server
from .module import Module
from realnet_server.models import VisibilityType, db, Item, Type, AclType, Acl, AccountGroup
from realnet_server.config import Config
import mimetypes

import boto3

cfg = Config()

session = boto3.Session(
    aws_access_key_id=cfg.get_s3_key(),
    aws_secret_access_key=cfg.get_s3_secret(),
    region_name=cfg.get_s3_region()
)

ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'md', 'csv', 'txt', 'zip', 'html', 'xml', 'json', 'mov', 'mp4', 'asf', 'avi'}

class Default(Module):

    def is_derived_from(self, type, type_name):
        if type.name == type_name:
            return True
        if type.base:
            return self.is_derived_from(type.base, type_name)

        return False

    def merge_attributes(self, left_item, right_item):
        if left_item.attributes and right_item.attributes:
            return left_item.attributes | right_item.attributes
        elif left_item.attributes:
            return left_item.attributes
        else:
            return right_item.attributes

    def get_type_attributes(self, type):
        result = {}
        if type.base:
            base_attrs = self.get_type_attributes(type.base)
            if base_attrs:
                result = result | base_attrs
        if type.attributes:
            result = result | type.attributes

        return result

    def get_instance_attributes(self, instance):
        result = self.get_type_attributes(instance.type)
        if instance.attributes:
            result = result | instance.attributes
        return result
            
            
    def is_item_public(self, item):

        if [acl for acl in item.acls if acl.type == AclType.public]:
            return True

        return False

    def can_account_execute_item(self, account, item):
        
        if [acl for acl in item.acls if acl.type == AclType.public]:
            return True

        if [acl for acl in item.acls if acl.type == AclType.user and acl.name == account.username and 'e' in acl.permission]:
            return True

        account_groups = set([ag.name for ag in AccountGroup.query.filter(AccountGroup.account_id == account.id)])

        if [acl for acl in item.acls if acl.type == AclType.group and acl.name in account_groups and 'e' in acl.permission]:
            return True

        account_group = AccountGroup.query.filter(AccountGroup.group_id == item.group_id, AccountGroup.account_id == account.id).first()

        if account_group:
            return True

        if item.owner_id == account.id:
            return True


    def can_account_message_item(self, account, item):

        if [acl for acl in item.acls if acl.type == AclType.public]:
            return True

        if [acl for acl in item.acls if acl.type == AclType.user and acl.name == account.username and 'm' in acl.permission]:
            return True

        account_groups = set([ag.name for ag in AccountGroup.query.filter(AccountGroup.account_id == account.id)])

        if [acl for acl in item.acls if acl.type == AclType.group and acl.name in account_groups and 'm' in acl.permission]:
            return True

        account_group = AccountGroup.query.filter(AccountGroup.group_id == item.group_id, AccountGroup.account_id == account.id).first()

        if account_group:
            return True

        if item.owner_id == account.id:
            return True


    def can_account_read_item(self, account, item):

        if [acl for acl in item.acls if acl.type == AclType.public]:
            return True

        if [acl for acl in item.acls if acl.type == AclType.user and acl.name == account.username and ('r' in acl.permission or 'w' in acl.permission)]:
            return True

        ags = AccountGroup.query.filter(AccountGroup.account_id == account.id).all()
        account_groups = set([ag.group.name for ag in ags])

        if [acl for acl in item.acls if acl.type == AclType.group and acl.name in account_groups and ('r' in acl.permission or 'w' in acl.permission)]:
            return True

        account_group = AccountGroup.query.filter(AccountGroup.group_id == item.group_id, AccountGroup.account_id == account.id).first()

        if account_group:
            return True

        if item.owner_id == account.id:
            return True


    def can_account_write_item(self, account, item):

        if [acl for acl in item.acls if
            acl.type == AclType.user and acl.name == account.username and 'w' in acl.permission]:
            return True

        account_groups = set([ag.group.name for ag in AccountGroup.query.filter(AccountGroup.account_id == account.id)])

        if [acl for acl in item.acls if
            acl.type == AclType.group and acl.name in account_groups and 'w' in acl.permission]:
            return True

        account_group = AccountGroup.query.filter(AccountGroup.group_id == item.group_id, AccountGroup.account_id == account.id).first()

        if account_group:
            return True

        if item.owner_id == account.id:
            return True


    def can_account_delete_item(self, account, item):
        
        account_group = AccountGroup.query.filter(
            AccountGroup.group_id == item.group_id, AccountGroup.account_id == account.id).first()
        
        if account_group:
            return True

        return item.owner_id == account.id

    def filter_readable_items(self, account, items_json):
        return [i for i in json.loads(items_json) if self.can_account_read_item(account, Item(**i))] if items_json else []

    def allowed_file(self, filename):
        return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

    def create_item(self, parent_item=None, **kwargs):
        item_name = None
        item_owner_id = None
        item_group_id = None
        item_type_id = None
        item_attributes = None
        item_parent_id = None
        item_location = None
        item_visibility = None
        item_tags = None
        item_is_public = False
        item_valid_from = None
        item_valid_to = None
        item_status = None
        item_linked_item_id = None

        for key, value in kwargs.items():
            # print("%s == %s" % (key, value))
            if key == 'name':
                item_name = value
            elif key == 'owner_id':
                item_owner_id = value
            elif key == 'group_id':
                item_group_id = value
            elif key == 'type_id':
                item_type_id = value
            elif key == 'attributes':
                item_attributes = value
            elif key == 'tags':
                item_tags = value
            elif key == 'location':
                data = json.loads(value)
                if data['type'] == 'Point':
                    item_location = 'SRID=4326;POINT({0} {1})'.format(data['coordinates'][0], data['coordinates'][1])
                else:
                    item_location = 'SRID=4326;POLYGON(('
                    for ii in data['coordinates'][0]:
                        item_location = item_location + '{0} {1},'.format(ii[0], ii[1])
                    item_location = item_location[0:-1] + '))'
            elif key == 'visibility':
                item_visibility = value
            elif key == 'public':
                item_is_public = (value.lower() == "true")
            elif key == 'valid_from':
                item_valid_from = value
            elif key == 'valid_to':
                item_valid_to = value
            elif key == 'status':
                item_status = value
            elif key == 'linked_item_id':
                item_linked_item_id = value

        if parent_item:
            item_parent_id = parent_item.id

        target_type = Type.query.filter(Type.id == item_type_id).first()

        item = realnet_server.models.create_item(
            db=db,
            item_id=str(uuid.uuid4()),
            item_type_name=target_type.name,
            item_name=item_name,
            item_tags=item_tags,
            owner_id=item_owner_id,
            group_id=item_group_id,
            parent_item_id=item_parent_id,
            item_attributes=item_attributes,
            item_visibility=item_visibility,
            item_location=item_location,
            item_is_public=item_is_public,
            item_valid_from=item_valid_from,
            item_valid_to=item_valid_to,
            item_status=item_status,
            item_linked_item_id=item_linked_item_id)

        db.session.add(item)
        db.session.commit()
        return item

    def get_item_data(self, item):
        if item and item.attributes and 'blob_type' in item.attributes:
            if item.attributes['blob_type'] == 'local':
                path1 = os.path.join(os.getcwd(), 'storage')
                return os.path.join(path1, item.attributes['filename'])
            elif item.attributes['blob_type'] == 's3':
                s3 = session.resource('s3')
                bucket = s3.Bucket(cfg.get_s3_bucket())
                s3_obj = bucket.Object(item.attributes['s3_blob_id']).get()
                return {'s3_obj': s3_obj, 'mimetype': item.attributes['mime_type'], 'filename': item.attributes['filename']}

        return None

    def update_item_data(self, item, storage):
        content_type = storage.content_type
        if storage.filename and content_type is None:
            content_type = mimetypes.guess_type(storage.filename)[0] or 'application/octet-stream'
        if item:
            cfg = Config()
            blob_type = cfg.get_storage_type()
            if item.attributes and 'blob_type' in item.attributes:
                blob_type = item.attributes['blob_type']
            if blob_type == 'local':
                path = os.path.join(item.attributes['path'], storage.filename)
                storage.save(path)
                item.attributes['content_length'] = os.stat(path).st_size
                item.attributes['content_type'] = content_type
                item.attributes['filename'] = storage.filename
                item.attributes['mime_type'] = content_type
                db.session.commit()
                return {'created': False, 'updated': True}
            elif blob_type == 's3':
                s3 = session.resource('s3')
                bucket = s3.Bucket(cfg.get_s3_bucket())
                bucket.Object(item.attributes['s3_blob_id']).put(Body=storage)
                item.attributes['content_length'] = storage.content_length,
                item.attributes['content_type'] = content_type,
                item.attributes['filename'] = storage.filename,
                item.attributes['mime_type'] = storage.mimetype,
                db.session.commit()
                return {'created': False, 'updated': True}

        return {'created': False, 'updated': False}

    def delete_item_data(self, item):
        file = Item.query.filter(Item.id == item.id).first()
        #TODO
        if file:
            pass

        return False


    def delete_item(self, item):
        db.session.delete(item)
        db.session.commit()

    def update_item(self, item, **kwargs):
        # print(kwargs.items())
        for key, value in kwargs.items():
            print("%s == %s" % (key, value))
            if key == 'name':
                item.name = value
            elif key == 'parent_id':
                item.parent_id = value
            elif key == 'attributes':
                item.attributes = value
            elif key == 'location':
                item_location = ''
                if value:
                    data = json.loads(value)
                    if data['type'] == 'Point':
                        item_location = 'SRID=4326;POINT({0} {1})'.format(data['coordinates'][0], data['coordinates'][1])
                    elif data['type'] == 'Polygon':
                        item_location = 'SRID=4326;POLYGON(('
                        for ii in data['coordinates'][0]:
                            item_location = item_location + '{0} {1},'.format(ii[0], ii[1])
                        item_location = item_location[0:-1] + '))'
                else:
                    item_location = None
                item.location = item_location
            elif key == 'valid_from':
                item.valid_from = value
            elif key == 'valid_to':
                item.valid_to = value
            elif key == 'status':
                item.status = value
            elif key == 'tags':
                item.tags = value
            elif key == 'linked_item_id':
                item.linked_item_id = value

        db.session.commit()

    def get_items(self, id):
        return Item.query.filter(Item.parent_id == id).all()

    def get_item(self, id):
        return Item.query.filter(Item.id == id).first()

    def invoke(self, item, arguments):
        func = item
        if func:
            code = func.attributes.code
            if code:
                result = dict()
                safe_list = ['self', 'func', 'arguments', 'result']
                safe_dict = dict([(k, locals().get(k, None)) for k in safe_list])
                eval(func.code, None, safe_dict)
                return result
        else:
            return None

    def message(self, item, arguments):
        return None

    def import_file(self, item, storage):
        cfg = Config()
        content_type = storage.content_type
        if storage.filename and content_type is None:
            content_type = mimetypes.guess_type(storage.filename)[0] or 'application/octet-stream'

        target_type = Type.query.filter(Type.name == 'File').first()

        if content_type.startswith('image/'):
            target_type = Type.query.filter(Type.name == 'Image').first()
        elif content_type.startswith('application/pdf') or content_type.startswith('text/plain') or storage.filename.endswith('.md'):
            target_type = Type.query.filter(Type.name == 'Document').first()
            if storage.filename.endswith('.md'):
                content_type = 'text/markdown'
        elif content_type.startswith('text/html'):
            target_type = Type.query.filter(Type.name == 'Page').first()
        elif content_type.startswith('video/'):
            target_type = Type.query.filter(Type.name == 'Video').first()
        elif content_type.startswith('application/x-zip-compressed'):
            target_type = Type.query.filter(Type.name == 'File').first()
        elif content_type.startswith('text/csv'):
            target_type = Type.query.filter(Type.name == 'File').first()
        else:
            target_type = Type.query.filter(Type.name == 'File').first()

        if not target_type:
            return  {'created': False, 'updated': False}
        
        if cfg.get_storage_type() == 'local':
            basepath = cfg.get_storage_path()
            path = os.path.join(basepath, storage.filename)
            storage.save(path)
            target = Item(id=str(uuid.uuid4()),
                            name=storage.filename,
                            type_id=target_type.id,
                            attributes={
                                'blob_type': 'local',
                                'path': basepath,
                                'content_length': os.stat(path).st_size,
                                'content_type': content_type,
                                'filename': storage.filename,
                                'mime_type': content_type
                                },
                            owner_id=item.owner_id,
                            group_id=item.group_id,
                            parent_id=item.id)
            
            db.session.add(target)
            db.session.commit()
            return {'created': True, 'updated': False}
        elif cfg.get_storage_type() == 's3':
            basepath = cfg.get_storage_path()
            s3 = session.resource('s3')
            bucket = s3.Bucket(cfg.get_s3_bucket())
            blob_id = str(uuid.uuid4())
            res = bucket.Object(blob_id).put(Body=storage)
            target = Item(id=str(uuid.uuid4()),
                          name=storage.filename,
                            type_id=target_type.id,
                            attributes={
                                'blob_type': 's3',
                                's3_blob_id': blob_id,
                                'content_length': storage.content_length,
                                'content_type': content_type,
                                'filename': storage.filename,
                                'mime_type': content_type
                                },
                            owner_id=item.owner_id,
                            group_id=item.group_id,
                            parent_id=item.id)
            
            db.session.add(target)
            db.session.commit()
            return {'created': True, 'updated': False}


    def perform_search(self, id, account, data, public=False):
        
        type_names = data.get('type_names')
        if type_names:
            data['type_names'] = type_names

        tags = data.get('tags')
        if tags:
            data['tags'] = tags

        name = data.get('name')
        if name:
            data['name'] = name
        
        parent_id = data.get('parent_id')
        if parent_id:
            data['parent_id'] = parent_id

        location = data.get('location')
        if location:
            data['location'] = location

        valid_from = data.get('valid_from')
        if valid_from:
            data['valid_from'] = valid_from

        valid_to = data.get('valid_to')
        if valid_to:
            data['valid_to'] = valid_to

        status = data.get('status')
        if status:
            data['status'] = status

        # TODO below

        keys = data.get('key')
        if keys:
            data['keys'] = keys

        values = data.get('values')
        if values:
            data['values'] = values

        visibility = data.get('visibility')
        if visibility:
            data['visibility'] = visibility

        conditions = []

        if type_names:
            type_ids = [ti.id for ti in Type.query.filter(Type.name.in_(type_names)).all()]
            derived_type_ids = [ti.id for ti in Type.query.filter(Type.base_id.in_(type_ids)).all()]
            conditions.append(Item.type_id.in_(list(set(type_ids + derived_type_ids))))

        # if tags:
        #    conditions.append(Item.tags.contains(tags))
        
        if name:
            conditions.append(Item.name.ilike('{}%'.format(unquote(str(name)))))
        
        if parent_id:
            conditions.append(Item.parent_id == parent_id)
        else:
            conditions.append(Item.parent_id == None)

        if location:
            # range = (0.00001) * float(radius)
            # ST_AsText(ST_GeomFromGeoJSON('{"type":"Point","coordinates":[-48.23456,20.12345]}'))
            conditions.append(func.ST_DWithin(Item.location, 'SRID=4326;{}'.format(func.ST_AsText(func.ST_GeomFromGeoJSON(location))), range))

        if valid_from:
            conditions.append(Item.valid_from >= valid_from)

        if valid_to:
            conditions.append(Item.valid_to <= valid_to)

        if status:
            conditions.append(Item.status == status)

        
        if keys and values:
            for kv in zip(keys, values):
                conditions.append(Item.attributes[kv[0]].astext == kv[1])

        if visibility:
            conditions.append(Item.visibility == VisibilityType[visibility])

        if public:
            if not conditions:
                return []
            else:
                return Item.query.filter(*conditions).all()
        else:
            if not conditions:
                conditions.append(Item.parent_id == account.home_id)
            
        return Item.query.filter(*conditions).all()
