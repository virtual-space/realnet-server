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