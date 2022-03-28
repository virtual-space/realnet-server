import uuid
import os
import json

from sqlalchemy import null
from .module import Module
from realnet_server.models import db, Item, Blob, BlobType
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

        if parent_item:
            item_parent_id = parent_item.id

        item = Item(id=str(uuid.uuid4()),
                    name=item_name,
                    owner_id=item_owner_id,
                    group_id=item_group_id,
                    type_id=item_type_id,
                    parent_id=item_parent_id,
                    attributes=item_attributes,
                    visibility=item_visibility,
                    location=item_location)
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
                blob.content_length = storage.content_length,
                blob.content_type = content_type,
                blob.filename = storage.filename,
                blob.mime_type = storage.mimetype,
                db.session.commit()
                return {'created': False, 'updated': True}
        else:
            cfg = Config()
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
                path = os.path.join(basepath, storage.filename)
                s3 = session.resource('s3')
                bucket = s3.Bucket(cfg.get_s3_bucket())
                blob_id = str(uuid.uuid4())
                res = bucket.Object(blob_id).put(Body=storage)
                blob = Blob(id=blob_id,
                            type=BlobType.s3,
                            data={},
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
        return json.dumps([i.to_dict() for i in Item.query.filter(Item.parent_id == item['id'])])

    def get_item(self, item):
        retrieved_item = Item.query.filter(Item.id == item.id).first()
        if retrieved_item:
            return json.dumps({'id': retrieved_item.id,
                            'name': retrieved_item.name,
                            'attributes': retrieved_item.attributes,
                            'type': retrieved_item.type.to_dict(),
                            'parent_id': retrieved_item.parent_id})

        return None
