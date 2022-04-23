import uuid
import os
import json

from sqlalchemy import false, null

from sqlalchemy.sql import func, and_, or_, not_, functions
try:
    from urllib.parse import unquote  # PY3
except ImportError:
    from urllib import unquote  # PY2

import realnet_server
from .module import Module
from realnet_server.models import VisibilityType, db, Item, Blob, BlobType, Type, create_item
from realnet_server.config import Config
import mimetypes

import boto3

cfg = Config()

session = boto3.Session(
    aws_access_key_id=cfg.get_s3_key(),
    aws_secret_access_key=cfg.get_s3_secret(),
    region_name=cfg.get_s3_region()
)

class Default(Module):

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
                if value['type'] == 'Point':
                    item_location = 'SRID=4326;POINT({0} {1})'.format(value['coordinates'][0], value['coordinates'][1])
                else:
                    item_location = 'SRID=4326;POLYGON(('
                    for ii in value['coordinates'][0]:
                        item_location = item_location + '{0} {1},'.format(ii[0], ii[1])
                    item_location = item_location[0:-1] + '))'
            elif key == 'visibility':
                item_visibility = value
            elif key == 'public':
                item_is_public = (value.lower() == "true")

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
            item_is_public=item_is_public)

        db.session.add(item)
        db.session.commit()
        return json.dumps(item.to_dict())

    def get_item_data(self, item):
        blob = Blob.query.filter(Blob.item_id == item.id).first()

        if blob:
            if blob.type == BlobType.local:
                path1 = os.path.join(os.getcwd(), 'storage')
                return os.path.join(path1, blob.filename)
            elif blob.type == BlobType.s3:
                s3 = session.resource('s3')
                bucket = s3.Bucket(cfg.get_s3_bucket())
                s3_obj = bucket.Object(blob.id).get()
                return {'s3_obj': s3_obj, 'mimetype': blob.mime_type, 'filename': blob.filename}

        return None

    def update_item_data(self, item, storage):
        cfg = Config()
        blob = Blob.query.filter(Blob.item_id == item.id).first()

        content_type = storage.content_type
        if storage.filename and content_type is None:
            content_type = mimetypes.guess_type(storage.filename)[0] or 'application/octet-stream'
        if blob:
            # update existing
            if blob.type == BlobType.local:
                path = os.path.join(blob.data['path'], storage.filename)
                storage.save(path)
                blob.content_length = os.stat(path).st_size
                blob.content_type = content_type
                blob.filename = storage.filename
                blob.mime_type = content_type
                db.session.commit()
                return {'created': False, 'updated': True}
            elif blob.type == BlobType.s3:
                s3 = session.resource('s3')
                bucket = s3.Bucket(cfg.get_s3_bucket())
                bucket.Object(blob.id).put(Body=storage)
                blob.data = storage
                blob.content_length = storage.content_length,
                blob.content_type = content_type,
                blob.filename = storage.filename,
                blob.mime_type = storage.mimetype,
                db.session.commit()
                return {'created': False, 'updated': True}
        else:
            if cfg.get_storage_type() == BlobType.local:
                basepath = cfg.get_storage_path()
                path = os.path.join(basepath, storage.filename)
                storage.save(path)
                blob = Blob(id=str(uuid.uuid4()),
                            type=BlobType.local,
                            data={'path': basepath},
                            content_length=os.stat(path).st_size,
                            content_type=content_type,
                            filename=storage.filename,
                            mime_type=content_type,
                            item_id=item.id)
                db.session.add(blob)
                db.session.commit()
                return {'created': True, 'updated': False}
            elif cfg.get_storage_type() == BlobType.s3:
                basepath = cfg.get_storage_path()
                #path = os.path.join(basepath, storage.filename)
                s3 = session.resource('s3')
                bucket = s3.Bucket(cfg.get_s3_bucket())
                blob_id = str(uuid.uuid4())
                res = bucket.Object(blob_id).put(Body=storage)
                blob = Blob(id=blob_id,
                            type=BlobType.s3,
                            data=storage,
                            content_length=storage.content_length,
                            content_type=content_type,
                            filename=storage.filename,
                            mime_type=storage.mimetype,
                            item_id=item.id)
                db.session.add(blob)
                db.session.commit()
                return {'created': True, 'updated': False}

        return {'created': False, 'updated': False}

    def delete_item_data(self, item):
        blob = Blob.query.filter(Blob.item_id == item.id).first()

        if blob:
            if blob.type == BlobType.local:
                path1 = os.path.join(os.getcwd(), 'storage')
                os.remove(os.path.join(path1, blob.filename))
                db.session.delete(blob)
                db.session.commit()
                return True
            elif blob.type == BlobType.s3:
                s3 = session.resource('s3')
                bucket = s3.Bucket(cfg.get_s3_bucket())
                bucket.Object(blob.id).delete()
                db.session.delete(blob)
                db.session.commit()
                return True

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
                    if value['type'] == 'Point':
                        item_location = 'SRID=4326;POINT({0} {1})'.format(value['coordinates'][0], value['coordinates'][1])
                    elif value['type'] == 'Polygon':
                        item_location = 'SRID=4326;POLYGON(('
                        for ii in value['coordinates'][0]:
                            item_location = item_location + '{0} {1},'.format(ii[0], ii[1])
                        item_location = item_location[0:-1] + '))'
                else:
                    item_location = None
                item.location = item_location

        db.session.commit()

    def get_items(self, item):
        id = item.id if isinstance(item, Item) else item['id']
        return json.dumps([i.to_dict() for i in Item.query.filter(Item.parent_id == id)])

    def get_item(self, item):
        retrieved_item = Item.query.filter(Item.id == item.id).first()
        if retrieved_item:
            return json.dumps({'id': retrieved_item.id,
                            'name': retrieved_item.name,
                            'attributes': retrieved_item.attributes,
                            'type': retrieved_item.type.to_dict(),
                            'parent_id': retrieved_item.parent_id,
                            'items': [i.to_dict() for i in retrieved_item.items]})

        return None

    def perform_search(self, account, data, public=False):
        
        home = data.get('home')
        if home:
            data['home'] = home

        parent_id = data.get('parent_id')
        if parent_id:
            data['parent_id'] = parent_id

        my_items = data.get('my_items')
        if my_items:
            data['my_items'] = my_items

        name = data.get('name')
        if name:
            data['name'] = name

        type_names = data.get('type_names')

        if type_names:
            data['type_names'] = type_names

        keys = data.get('key')

        if keys:
            data['keys'] = keys

        values = data.get('values')

        if values:
            data['values'] = values

        lat = data.get('lat')

        if lat:
            data['lat'] = lat

        lng = data.get('lng')

        if lng:
            data['lng'] = lng
        
        radius = data.get('radius', 100.00)

        if radius:
            data['radius'] = radius

        visibility = data.get('visibility')

        if visibility:
            data['visibility'] = visibility

        tags = data.get('tags')

        if tags:
            data['tags'] = tags

        conditions = []

        if home:
            folder = Item.query.filter(Item.parent_id == account.id, Item.name == 'Home').first()
            if folder:
                conditions.append(Item.parent_id == folder.id)
            else:
                conditions.append(Item.parent_id == None)
        elif parent_id:
            conditions.append(Item.parent_id == parent_id)
        elif my_items and account:
            conditions.append(Item.owner_id == account.id)


        if name:
            conditions.append(Item.name.ilike('{}%'.format(unquote(name))))

        if type_names:
            type_ids = [ti.id for ti in Type.query.filter(Type.name.in_(type_names)).all()]
            derived_type_ids = [ti.id for ti in Type.query.filter(Type.base_id.in_(type_ids)).all()]
            conditions.append(Item.type_id.in_(list(set(type_ids + derived_type_ids))))

        if keys and values:
            for kv in zip(keys, values):
                conditions.append(Item.attributes[kv[0]].astext == kv[1])

        if lat and lng:
            range = (0.00001) * float(radius)
            conditions.append(func.ST_DWithin(Item.location, 'SRID=4326;POINT({} {})'.format(lng, lat), range))

        if visibility:
            conditions.append(Item.visibility == VisibilityType[visibility])

        if tags:
            conditions.append(Item.tags.contains(tags))

        if public:
            if not conditions:
                return []
            else:
                return Item.query.filter(*conditions).all()
        else:
            if not conditions:
                conditions.append(Item.parent_id == account.home_id)
            
        return Item.query.filter(*conditions).all()
