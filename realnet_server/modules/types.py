from .default import Default

import json
import uuid

from sqlalchemy import false, null

from sqlalchemy.sql import func, and_, or_, not_, functions
try:
    from urllib.parse import unquote  # PY3
except ImportError:
    from urllib import unquote  # PY2

from realnet_server.models import Instance, db, Item, Type

class Types(Default):
    

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
            conditions.append(Type.name.ilike('{}%'.format(unquote(name))))

        if keys and values:
            for kv in zip(keys, values):
                conditions.append(Type.attributes[kv[0]].astext == kv[1])

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
                    type = t) for t in Type.query.all()]
        else:
            return [Item( id="{}_{}".format(id, t.id),
                    name=t.name,
                    attributes=t.attributes,
                    owner_id=t.owner_id,
                    group_id=t.group_id,
                    type_id=t.id,
                    parent_id="{}_{}".format(t.base_id, t.base_id),
                    type = t) for t in Type.query.filter(*conditions).all()]

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
                            type = t) for t in Type.query.all()]

    def get_item(self, id):
        target_id = id
        base_id = id
        ids = id.split("_")
        if len(ids) > 1:
            target_id = ids[-1]
        if target_id != base_id:
            type = Type.query.filter(Type.id == target_id).first()
            return Item( id="{}_{}".format(base_id, target_id),
                            name=type.name,
                            attributes=type.attributes,
                            owner_id=type.owner_id,
                            group_id=type.group_id,
                            type_id=type.id,
                            parent_id=base_id,
                            type = type)
        else:
            #this is the query for all orgs
            typeapp_type = Type.query.filter(Type.name == 'TypeApp').first()
            t = Item.query.filter(Item.id == id).first()
            if t and typeapp_type:
                return Item( id=t.id,
                             name=t.name,
                             attributes=self.merge_attributes(typeapp_type, t),
                             owner_id=typeapp_type.owner_id,
                             group_id=typeapp_type.group_id,
                             type_id=typeapp_type.id,
                             type=typeapp_type)

        return None

    def create_item(self, parent_item=None, **kwargs):
        item_name = None
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
            elif key == 'parent_id':
                item_parent_id = value
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

        target_id = item_parent_id
        base_id = item_parent_id
        ids = item_parent_id.split("_")
        if len(ids) > 1:
            base_id = ids[0]
            target_id = ids[-1]

        type = Type(id=str(uuid.uuid4()),
                           name=item_name,
                           icon=item_attributes.get('icon', 'approval'),
                           attributes=item_attributes,
                           owner_id=item_owner_id,
                           group_id=item_group_id,
                           module=item_attributes.get('module', 'default'))
        
        db.session.add(type)
        
        db.session.commit()
            
        return Item( id="{}_{}".format(id, type.id),
                     name=type.name,
                     attributes=type.attributes,
                     owner_id=type.owner_id,
                     group_id=type.group_id,
                     type_id=type.id,
                     parent_id= "{}_{}".format(id, type.base_id),
                     type = type)


