from .default import Default

import json
from sqlalchemy import false, null

from sqlalchemy.sql import func, and_, or_, not_, functions
try:
    from urllib.parse import unquote  # PY3
except ImportError:
    from urllib import unquote  # PY2

from realnet_server.models import VisibilityType, db, Item, Blob, BlobType, Type, create_item, Group

class Groups(Default):
    

    def perform_search(self, id, account, data, public=False):
        
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

        if name:
            conditions.append(Group.name.ilike('{}%'.format(unquote(name))))

        if keys and values:
            for kv in zip(keys, values):
                conditions.append(Group.attributes[kv[0]].astext == kv[1])

        # if tags:
        #    conditions.append(Item.tags.contains(tags))

        if not conditions:
            return [Item( id="{}_{}".format(id, t.id),
                    name=t.name,
                    attributes=t.attributes,
                    owner_id=t.owner_id,
                    group_id=t.group_id,
                    type_id=t.id,
                    parent_id="{}_{}".format(t.base_id, t.base_id),
                    type = t) for t in Group.query.all()]
        else:
            return [Item( id="{}_{}".format(id, t.id),
                    name=t.name,
                    attributes=t.attributes,
                    owner_id=t.owner_id,
                    group_id=t.group_id,
                    type_id=t.id,
                    parent_id="{}_{}".format(t.base_id, t.base_id),
                    type = t) for t in Group.query.filter(*conditions).all()]

    def update_item(self, item, **kwargs):
        # print(kwargs.items())
        for key, value in kwargs.items():
            print("%s == %s" % (key, value))
            if key == 'name':
                item.name = value
            elif key == 'attributes':
                item.attributes = value
        
        db.session.commit()

    def get_items(self, id):
        return [Item( id="{}_{}".format(id, t.id),
                            name=t.name,
                            attributes=t.attributes,
                            owner_id=t.owner_id,
                            group_id=t.group_id,
                            type_id=t.id,
                            parent_id= "{}_{}".format(id, t.base_id),
                            type = t) for t in Group.query.all()]

    def get_item(self, id):
        target_id = id
        base_id = id
        ids = id.split("_")
        if len(ids) > 1:
            target_id = ids[-1]
        t = Group.query.filter(Group.id == target_id).first()
        if t:
            return Item( id="{}_{}".format(id, t.id),
                            name=t.name,
                            attributes=t.attributes,
                            owner_id=t.owner_id,
                            group_id=t.group_id,
                            type_id=t.id,
                            parent_id= "{}_{}".format(id, t.base_id),
                            type = t)

        return None


