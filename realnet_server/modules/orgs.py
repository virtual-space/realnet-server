from .default import Default
from realnet_server.models import AccountGroup, AccountType, GroupRoleType, create_client, create_item, db, Org, Type, Item, Group, Account, Client, create_account
try:
    from urllib.parse import unquote  # PY3
except ImportError:
    from urllib import unquote  # PY2
import uuid

class Orgs(Default):

    def create_role_for_account(self, account_id, group_id, org_id, role_type_id):
        account = Account.query.filter(Account.id == account_id).first()
        group = Group.query.filter(Group.id == group_id).first()
        org = Org.query.filter(Org.id == org_id).first()
        role_type = Type.query.filter(Type.id == role_type_id).first()

        if account and group and org and role_type:
            item = create_item(db,
                item_type_name=role_type.name,
                item_id=str(uuid.uuid4()),
                item_name=role_type.name,
                item_attributes=role_type.attributes,
                item_location=None,
                item_visibility=None,
                item_tags=None,
                item_is_public=None,
                parent_item_id=account.id,
                owner_id=account.id,
                group_id=group.id
                )
            db.session.add(item)
            db.session.commit()
    
            return item
        
        return None

    def create_client(self, instance, owner_id, group_id, org_id):
        attributes = self.get_instance_attributes(instance)
        client  = create_client(name=instance.name,
                                client_id=attributes.get('client_id'),
                                client_secret=attributes.get('client_secret'),
                                uri=attributes.get('uri'),
                                grant_types=attributes.get('grant_types'),
                                redirect_uris=attributes.get('redirect_uris'),
                                response_types=attributes.get('response_types'),
                                scope=attributes.get('scope'),
                                auth_method=attributes.get('auth_method'),
                                account_id=owner_id,
                                org_id=org_id)
        db.session.add(client)
        db.session.commit()
        return Item( id=client.id,
                        name=client.name,
                        attributes=self.merge_attributes(instance.type, client),
                        owner_id=owner_id,
                        group_id=group_id,
                        type_id=instance.type.id,
                        type = instance.type)
        
        return None

    def create_group(self, instance, owner_id, group_id, org_id ):
        group_attributes = self.get_instance_attributes(instance)
        group = None
        if group_attributes.get('root') == 'true':
            group = Group.query.filter(Group.id == group_id).first()
        else:
            group = Group(  id=str(uuid.uuid4()), 
                            name=instance.name, 
                            org_id=org_id, 
                            attributes=self.get_instance_attributes(instance))
            db.session.add(group)
            db.session.commit()

        for account_instance in instance.type.instances:
            if self.is_derived_from(account_instance.type, 'Account'):
                attributes = self.get_instance_attributes(account_instance)
                
                if attributes.get('root') != 'true':
                    username = attributes.get('username')
                    password = attributes.get('password')
                    email = attributes.get('email')
                    account = Account(id=str(uuid.uuid4()),
                                        type=AccountType[attributes.get('account_type').lower()],
                                        username=username,
                                        email=email,
                                        group_id=group.id)
                    if password:
                        account.set_password(password)
                    db.session.add(account)

                    account_group = AccountGroup(id=str(uuid.uuid4()),
                                                    account_id=account.id,
                                                    group_id=group.id,
                                                    role_type=GroupRoleType.contributor)
                    db.session.add(account_group)
                    db.session.commit()

                    account_item = create_item(db,
                            item_type_name=account.type.name,
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
                    db.session.add(account_item)
                    db.session.commit()

                    for role_instance in account_instance.type.instances:
                        attributes = self.get_instance_attributes(role_instance)
                        role_item = create_item(db,
                            item_type_name=role_instance.type.name,
                            item_id=str(uuid.uuid4()),
                            item_name=role_instance.type.name,
                            item_attributes=attributes,
                            item_location=None,
                            item_visibility=None,
                            item_tags=None,
                            item_is_public=None,
                            parent_item_id=account.id,
                            owner_id=account.id,
                            group_id=group.id
                            )
                        db.session.add(role_item)
                        db.session.commit()
        
        return Item( id=group.id,
                        name=group.name,
                        attributes=self.merge_attributes(instance.type, group),
                        owner_id=owner_id,
                        group_id=group_id,
                        type_id=instance.type.id,
                        type = instance.type)

    def get_client_attributes(self, client, type):
        attributes = self.merge_attributes(type, client)
        attributes = attributes | client.client_metadata
        attributes = attributes | client.client_info
        return attributes

    def perform_search(self, id, account, data, public=False):
        
        name = data.get('name')
        if name:
            data['name'] = name

        keys = data.get('key')

        if keys:
            data['keys'] = keys

        values = data.get('values')

        if values:
            data['values'] = values

        conditions = []

        if name:
            conditions.append(Org.name.ilike('{}%'.format(unquote(name))))

        if keys and values:
            for kv in zip(keys, values):
                conditions.append(Org.attributes[kv[0]].astext == kv[1])

        type = Type.query.filter(Type.name == 'Org').first()

        if type:
            if not conditions:
                return [Item( id=t.id,
                    name=t.name,
                    attributes=t.attributes,
                    owner_id=account.id,
                    group_id=t.id,
                    type_id=type.id,
                    type = type) for t in Org.query.all()]
            else:
                return [Item( id=t.id,
                        name=t.name,
                        attributes=t.attributes,
                        owner_id=account.id,
                        group_id=t.id,
                        type_id=type.id,
                        parent_id=id,
                        type = type) for t in Org.query.filter(*conditions).all()]
        return []

    def get_item(self, id):
        target_id = id
        base_id = id
        ids = id.split("_")
        if len(ids) > 1:
            base_id = ids[0]
            target_id = ids[-1]
        if target_id != base_id:
            if len(ids) == 3:
                # this is a group or a client
                org_type = Type.query.filter(Type.name == 'Org').first()
                org = Org.query.filter(Org.id == ids[1]).first()
                if org and org_type:
                    # is this a group?
                    group = Group.query.filter(Group.id == target_id, Group.org_id == org.id).first()
                    if group:
                        group_type = Type.query.filter(Type.name == 'Group').first()
                        if group_type:
                            account_type = Type.query.filter(Type.name == 'Account').first()
                            accounts = [Item( id="{}_{}_{}_{}".format(base_id, org.id, group.id, tt.id),
                                                name=tt.username,
                                                attributes=self.merge_attributes(account_type, tt),
                                                owner_id=org_type.owner_id,
                                                group_id=org_type.group_id,
                                                type_id=org_type.id,
                                                type = account_type) for tt in Account.query.filter(Account.group_id == group.id)]
                            return Item( id="{}_{}_{}".format(base_id, org.id, group.id),
                                        name=group.name,
                                        attributes=self.merge_attributes(group_type, group),
                                        owner_id=group_type.owner_id,
                                        group_id=group_type.group_id,
                                        type_id=group_type.id,
                                        items=accounts,
                                        type = group_type)
                    # is this a client?
                    client = Client.query.filter(Client.id == target_id, Client.org_id == org.id).first()
                    if client:
                        client_type = Type.query.filter(Type.name == 'Client').first()
                        if client_type:
                            return Item( id="{}_{}_{}".format(base_id, org.id, client.id),
                                        name=client.name,
                                        attributes=self.get_client_attributes(client, client_type),
                                        owner_id=client_type.owner_id,
                                        group_id=client_type.group_id,
                                        type_id=client_type.id,
                                        type = client_type)
            elif len(ids) == 4:
                #this is an account
                account = Account.query.filter(Account.id == target_id).first()
                if account:
                    account_type = Type.query.filter(Type.name == 'Account').first()
                    if account_type:
                        return Item( id="{}_{}_{}_{}".format(base_id, ids[1], ids[2], target_id),
                                    name=account.username,
                                    attributes=self.merge_attributes(account_type, account),
                                    owner_id=account_type.owner_id,
                                    group_id=account_type.group_id,
                                    type_id=account_type.id,
                                    type = account_type)

                    
        else:
            #this is the query the org
            org_app = Item.query.filter(Item.id == target_id).first()
            org_type = Type.query.filter(Type.name == 'Org').first()
            if org_app and org_type:
                org_group = Group.query.filter(Group.id == org_app.group_id).first()
                if org_group:
                    org = Org.query.filter(Org.id == org_group.org_id).first()
                    group_type = Type.query.filter(Type.name == 'Group').first()
                    groups = [Item( id="{}_{}_{}".format(base_id, org.id, tt.id),
                                        name=tt.name,
                                        attributes=self.merge_attributes(group_type, tt),
                                        owner_id=org_type.owner_id,
                                        group_id=org_type.group_id,
                                        type_id=org_type.id,
                                        type = group_type) for tt in Group.query.filter(Group.org_id == org.id)]
                    client_type = Type.query.filter(Type.name == 'Client').first()
                    clients = [Item( id="{}_{}_{}".format(base_id, org.id, tt.id),
                                        name=tt.name,
                                        attributes=self.get_client_attributes(tt, client_type),
                                        owner_id=org_type.owner_id,
                                        group_id=org_type.group_id,
                                        type_id=org_type.id,
                                        type = client_type) for tt in Client.query.filter(Client.org_id == org.id)]
                    return Item( id=id,
                                name=org.name,
                                attributes=self.merge_attributes(org_type, org),
                                owner_id=org_type.owner_id,
                                group_id=org_type.group_id,
                                type_id=org_type.id,
                                items=[Item( id=tt.id,
                                        name=tt.name,
                                        attributes=tt.attributes,
                                        owner_id=tt.owner_id,
                                        group_id=tt.group_id,
                                        type_id=tt.type_id,
                                        type = tt.type) for tt in groups + clients],
                                type=org_type)

        return None

    def create_item(self, parent_item=None, **kwargs):
        item_name = None
        item_type_id = None
        item_attributes = None
        item_parent_id = None
        item_location = None
        item_owner_id = None
        item_group_id = None
        item_type = None
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

        if target_id != base_id:
            if len(ids) == 3:
                # create an account
                
                group = Group.query.filter(Group.id == ids[2]).first()
                org = Org.query.filter(Org.id == ids[1]).first()
                account_type = Type.query.filter(Type.id == item_type_id).first()

                if org and group and account_type:
                    username = item_attributes.get('username', item_name)
                    password = item_attributes.get('password')
                    email = item_attributes.get('email')
                    account = Account(id=str(uuid.uuid4()),
                           type=AccountType[account_type.name.lower()],
                           username=username,
                           email=email,
                           group_id=group.id)
                    if password:
                        account.set_password(password)

                    db.session.add(account)

                    account_group = AccountGroup(id=str(uuid.uuid4()),
                                                 account_id=account.id,
                                                 group_id=group.id,
                                                 role_type=GroupRoleType.contributor)
                    db.session.add(account_group)
                    db.session.commit()

                    item = create_item(db,
                        item_type_name=account.type.name,
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
            
                    return item
                else:
                    return None
            elif len(ids) == 4:
                # create a role
                account = Account.query.filter(Account.id == ids[3]).first()
                group = Group.query.filter(Group.id == ids[2]).first()
                org = Org.query.filter(Org.id == ids[1]).first()
                role_type = Type.query.filter(Type.id == item_type_id).first()

                if account and group and org and role_type:
                    item = create_item(db,
                        item_type_name=role_type.name,
                        item_id=str(uuid.uuid4()),
                        item_name=role_type.name,
                        item_attributes=role_type.attributes,
                        item_location=None,
                        item_visibility=None,
                        item_tags=None,
                        item_is_public=None,
                        parent_item_id=account.id,
                        owner_id=account.id,
                        group_id=group.id
                        )
                    db.session.add(item)
                    db.session.commit()
            
                    return item
                else:
                    return None

        else:
            # create an org
            type = Type.query.filter(Type.id == item_type_id).first()
            if type:
                if self.is_derived_from(type, 'Client'):
                    if parent_item:
                        group = Group.query.filter(Group.id == type.group_id).first()
                        if group:
                            client  = create_client(name=item_name,
                                                    client_id=item_attributes.get('client_id'),
                                                    client_secret=item_attributes.get('client_secret'),
                                                    uri=item_attributes.get('uri'),
                                                    grant_types=item_attributes.get('grant_types'),
                                                    redirect_uris=item_attributes.get('redirect_uris'),
                                                    response_types=item_attributes.get('response_types'),
                                                    scope=item_attributes.get('scope'),
                                                    auth_method=item_attributes.get('auth_method'),
                                                    account_id=type.owner_id,
                                                    org_id=group.org_id)
                            db.session.add(client)
                            db.session.commit()
                            return Item( id=client.id,
                                            name=client.name,
                                            attributes=self.merge_attributes(type, client),
                                            owner_id=type.owner_id,
                                            group_id=type.group_id,
                                            type_id=type.id,
                                            type = type)
                elif self.is_derived_from(type, 'Group'):
                    if parent_item:
                        owner_group = Group.query.filter(Group.id == type.group_id).first()
                        if owner_group:
                            group = Group(id=str(uuid.uuid4()), name=item_name, org_id=owner_group.org_id, attributes=item_attributes)
                            db.session.add(group)
                            db.session.commit()
                            for account_instance in type.instances:
                                if self.is_derived_from(account_instance.type, 'Account'):
                                    attributes = self.get_instance_attributes(account_instance)
                                    
                                    if attributes.get('root') != 'true':
                                        username = attributes.get('username')
                                        password = attributes.get('password')
                                        email = attributes.get('email')
                                        account = Account(id=str(uuid.uuid4()),
                                                            type=AccountType[attributes.get('account_type').lower()],
                                                            username=username,
                                                            email=email,
                                                            group_id=group.id)
                                        if password:
                                            account.set_password(password)
                                        db.session.add(account)

                                        account_group = AccountGroup(id=str(uuid.uuid4()),
                                                                        account_id=account.id,
                                                                        group_id=group.id,
                                                                        role_type=GroupRoleType.contributor)
                                        db.session.add(account_group)
                                        db.session.commit()

                                        account_item = create_item(db,
                                                item_type_name=account.type.name,
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
                                        db.session.add(account_item)
                                        db.session.commit()

                                        for role_instance in account_instance.type.instances:
                                            attributes = self.get_instance_attributes(role_instance)
                                            role_item = create_item(db,
                                                item_type_name=role_instance.type.name,
                                                item_id=str(uuid.uuid4()),
                                                item_name=role_instance.type.name,
                                                item_attributes=attributes,
                                                item_location=None,
                                                item_visibility=None,
                                                item_tags=None,
                                                item_is_public=None,
                                                parent_item_id=account.id,
                                                owner_id=account.id,
                                                group_id=group.id
                                                )
                                            db.session.add(role_item)
                                            db.session.commit()
                        
                            return Item( id=group.id,
                                            name=group.name,
                                            attributes=self.merge_attributes(type, group),
                                            owner_id=type.owner_id,
                                            group_id=type.group_id,
                                            type_id=type.id,
                                            type = type)
                elif self.is_derived_from(type, 'Org'):
                    org = Org.query.filter(Org.name == item_name).first()

                    if not org:
                        org = Org(id=str(uuid.uuid4()),
                                name=item_name)
                        db.session.add(org)
                        db.session.commit()

                    if type and self.is_derived_from(type, 'Org'):
                        for instance in type.instances:
                            if self.is_derived_from(instance.type, 'Client'):
                                self.create_client(instance,  item_owner_id, item_group_id, org.id)
                            elif self.is_derived_from(instance.type, 'Group'):
                                self.create_group(instance, item_owner_id, item_group_id, org.id)
                    
                        return Item( id="{}_{}".format(base_id, org.id),
                                            name=org.name,
                                            attributes=item_attributes,
                                            owner_id=item_owner_id,
                                            group_id=item_group_id,
                                            type_id=type.id,
                                            parent_id=base_id,
                                            type=type)

    def delete_item(self, item):
        ids = item.id.split('_')
        length = len(ids)
        #print("id list", ids)
        rows_to_delete = []
        if length == 1:
            pass #attempting to delete the 'org' module. This should raise an error.
        elif length == 2:
            pass #attempting to delete an org. This should raise an error.
        elif length == 3:
            #THIS WILL DELETE FROM BOTH TABLES IF THE ID IS IN BOTH.
            #attempting to delete a group, all accounts and all roles linked to it.
            #and/or delete a client.
            group_id = ids[-1]
            rows_to_delete.append(Group.query.filter(Group.id == group_id).first())
            for row in Account.query.filter(Account.group_id == group_id):
                rows_to_delete.append(row)
            for row in Item.query.filter(Item.group_id == group_id):
                rows_to_delete.append(row)
            for row in AccountGroup.query.filter(AccountGroup.group_id == group_id):
                rows_to_delete.append(row)
            rows_to_delete.append(Client.query.filter(Client.id == group_id).first())
        elif length == 4:
            #attempting to delete a account in a group, and all roles linked to that account
            account_id = ids[-1]
            rows_to_delete.append(Account.query.filter(Account.id == account_id).first())
            rows_to_delete.append(AccountGroup.query.filter(AccountGroup.account_id == account_id).first())
            for row in Item.query.filter(Item.owner_id == account_id):
                rows_to_delete.append(row)
        elif length == 5:
            #attempting to delete a role in an account
            item_id = ids[-1]
            rows_to_delete.append(Item.query.filter(Item.id == item_id).first)
        #print(rows_to_delete)
        for row in rows_to_delete:
            if(row is not None):
                db.session.delete(row)
        db.session.commit()