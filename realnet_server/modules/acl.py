from logging import error
from .default import Default
from realnet_server.models import AccountGroup, AccountType, GroupRoleType, create_client, create_item, db, Org, Type, Acl, Item, Group, Account, Client, create_account
try:
    from urllib.parse import unquote  # PY3
except ImportError:
    from urllib import unquote  # PY2
import uuid

class Acl(Default):

    def create_item(self, parent_item=None, **kwargs):
        target_item = None
        item_name = None 
        item_type = None #public/account/group
        item_permissions = '' #RWX etc
        item_target_id = None #target to grant permissions to
        item_owner_id = None #owner of this acl - going to default to owner of the passed item.
        item_item_id = None #required

        for key, value in kwargs.items():
            # print("%s == %s" % (key, value))
            if key == 'name':
                item_name = value
            elif key == 'type':
                item_type = value
            elif key == 'permissions':
                item_permissions = value
            elif key == 'target_id':
                item_target_id = value
            elif key == 'owner_id':
                item_owner_id = value
            elif key == 'item_id':
                item_item_id = value

        if not (item_type == 'account' or item_type == 'group' or item_type == 'public'):
            raise error('400: invalid ACL type provided.')

        if not item_target_id and item_type != 'public':
            raise error('400: no target ID and type is not public')

        if item_item_id:
            target_item = Item.query.filter(Item.id == item_item_id)
        else:
            raise error('400: no target item')

        if not item_name:
            item_name = "ACL for:" + target_item.name

        if not item_owner_id:
            item_owner_id = target_item.owner_id

        acl = Acl(id=str(uuid.uuid4()),
                           type=item_type,
                           name=item_name,
                           permission=item_permissions,
                           target_id=item_target_id,
                           owner_id=item_owner_id,
                           item_id=item_item_id)
        
        db.session.add(acl)
        db.session.commit()

    def delete_item(self, item):
        ids = item.id.split('_')
        acl = Acl.query.filter(Acl.id == ids[-1])
        db.session.delete(acl)
        db.session.commit()

    def update_item(self, item, **kwargs):
        ids = item.id.split('_')
        target_item = Acl.query.filter(Acl.id == ids[-1])

        for key, value in kwargs.items():
            # print("%s == %s" % (key, value))
            if key == 'name':
                target_item.name = value
            elif key == 'type':
                target_item.type = value
            elif key == 'permissions':
                target_item.permission = value
            elif key == 'target_id':
                target_item.target_id = value
            elif key == 'owner_id':
                target_item.owner_id = value
            elif key == 'item_id':
                target_item.item_id = value

        db.session.commit()

    def get_items(self, id):
        return Acl.query.filter(Acl.owner_id == id).all()

    def get_item(self, id):
        return Acl.query.filter(Acl.id == id).first()

    def perform_search(self, id, account, data, public=False):
        conditions = []
        name = data.get('name')
        target_id = data.get('target_id')
        owner_id = data.get('owner_id')
        item_id = data.get('item_id')

        if name:
            conditions.append(Acl.name.ilike('{}%'.format(unquote(str(name)))))
        if target_id:
            conditions.append(Acl.target_id == target_id)
        if owner_id:
            conditions.append(Acl.owner_id == owner_id)
        if item_id:
            conditions.append(Acl.item_id == item_id)

        if public:
            if not conditions:
                return []
            else:
                return Acl.query.filter(*conditions).all()
        else:
            if not conditions:
                conditions.append(Acl.owner_id == account.home_id)
            
        return Acl.query.filter(*conditions).all()