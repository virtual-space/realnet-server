import uuid
import os
import shutil
from .module import Module
from realnet_server.models import db, Item, Blob, BlobType
from realnet_server.config import Config
from flask import jsonify


class Default(Module):

    def create_item(self, parent_item=None, **kwargs):
        item_name = None
        item_owner_id = None
        item_group_id = None
        item_type_id = None
        item_attributes = None
        item_parent_id = None

        for key, value in kwargs.items():
            print("%s == %s" % (key, value))
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

        if parent_item:
            item_parent_id = parent_item.id

        item = Item(id=str(uuid.uuid4()),
                    name=item_name,
                    owner_id=item_owner_id,
                    group_id=item_group_id,
                    type_id=item_type_id,
                    parent_id=item_parent_id,
                    attributes=item_attributes)
        db.session.add(item)
        db.session.commit()
        return jsonify(item.to_dict())

    def get_item_data(self, item):
        blob = Blob.query.filter(Blob.item_id == item.id).first()

        if blob:
            path1 = os.path.join(os.getcwd(), 'storage')
            return os.path.join(path1, blob.filename)

        return None

    def update_item_data(self, item, storage):
        cfg = Config.init()
        storage_cfg = cfg.get_storage()
        blob = Blob.query.filter(Blob.item_id == item.id).first()

        if blob:
            # update existing
            if blob.type == BlobType.local:
                path = os.path.join(blob.data['path'], storage.filename)
                storage.save(path)
                blob.content_length = os.stat(path).st_size
                blob.content_type = storage.content_type
                blob.filename = storage.filename
                blob.mime_type = storage.mimetype
                db.session.commit()
            elif blob.type == BlobType.s3:
                pass
        else:
            if storage_cfg['type'] == 'local':
                basepath = './storage/'
                if not os.path.isdir(basepath):
                    os.mkdir(basepath)
                path = os.path.join(basepath, storage.filename)
                storage.save(path)
                blob = Blob(id=str(uuid.uuid4()),
                            type=BlobType.local,
                            data={'path': basepath},
                            content_length=os.stat(path).st_size,
                            content_type=storage.content_type,
                            filename=storage.filename,
                            mime_type=storage.mimetype,
                            item_id=item.id)
                db.session.add(blob)
                db.session.commit()
            elif storage_cfg['type'] == 's3':
                pass
            pass

    def delete_item_data(self, item):
        blob = Blob.query.filter(Blob.item_id == item.id).first()
        if blob:
            path1 = os.path.join(os.getcwd(), 'storage')
            os.remove(os.path.join(path1, blob.filename))
            db.session.delete(blob)
            db.session.commit()

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

        db.session.commit()

    def get_items(self, item):
        return jsonify([i.to_dict() for i in Item.query.filter(Item.parent_id == item.id)])

    def get_item(self, item):
        retrieved_item = Item.query.filter(Item.id == item.id).first()
        if retrieved_item:
            return jsonify({'id': retrieved_item.id,
                            'name': retrieved_item.name,
                            'attributes': retrieved_item.attributes,
                            'type': retrieved_item.type.to_dict(),
                            'parent_id': retrieved_item.parent_id})

        return None
