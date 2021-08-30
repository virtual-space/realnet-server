from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, Group, Account, AccountGroup, GroupRoleType
from sqlalchemy import or_
import uuid

def can_account_create_group(account):
    return True

def can_account_read_group(account, group):
    if account.group_id == group.id or account.group_id == group.parent_id:
        return True

    return False

def can_account_write_group(account, group):
    if account.group_id == group.id or account.group_id == group.parent_id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root \
                    or accountGroup.role_type == GroupRoleType.admin:
                return True

    return False

def can_account_delete_group(account, group):
    if account.group_id == group.id or account.group_id == group.parent_id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root \
                    or accountGroup.role_type == GroupRoleType.admin:
                return True

    return False

@app.route('/groups', methods=('GET', 'POST'))
@require_oauth()
def groups():
    if request.method == 'POST':
        request.on_json_loading_failed = lambda x: print('json parsing error: ', x)
        input_data = request.get_json(force=True, silent=False)
        if input_data:
            input_name = input_data['name']
            if input_name:
                if not can_account_create_group(account=current_token.account):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to create the group'), 403

                created = Group(id=str(uuid.uuid4()),
                                name=input_name,
                                parent_id=current_token.account.group_id)

                db.session.add(created)
                db.session.commit()

                return jsonify(created.to_dict()), 201
    else:
        return jsonify([q.to_dict() for q in Group.query.filter(Group.parent_id == current_token.account.group_id)])

@app.route('/groups/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_group(id):
    # 1. get the group
    group = Group.query.filter(or_(Group.id == id,
                                   Group.name == id),
                                   Group.parent_id == current_token.account.group_id).first()
    if group:
        
        if request.method == 'PUT':

            if not can_account_write_group(account=current_token.account, group=group):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to write to group'), 403

            input_data = request.get_json(force=True, silent=False)

            args = dict()

            if 'name' in input_data:
                group.name = input_data['name']
            
            db.session.commit()
            
            return jsonify(group.to_dict())

        elif request.method == 'DELETE':

            if not can_account_delete_group(account=current_token.account, group=group):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to delete this group'), 403

            db.session.delete(group)
            db.session.commit()

            return jsonify(isError=False,
                           message="Success",
                           statusCode=200,
                           data='deleted group {0}'.format(id)), 200
        else:
            if not can_account_read_group(account=current_token.account, group=group):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this group'), 403
            return jsonify(group.to_dict())

    return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='get_item {0}'.format(id)), 404

@app.route('/groups/<id>/accounts', methods=['GET', 'POST'])
@require_oauth()
def group_accounts(id):
    group = Group.query.filter(or_(Group.id == id,
                                   Group.name == id),
                                   Group.parent_id == current_token.account.group_id).first()
    if group:
        account = Account.query.filter(Account.id == current_token.account.id).first()
        if request.method == 'POST':

            input_data = request.get_json(force=True, silent=False)

            role = 'guest'
            username = None

            if 'role' in input_data:
                role = input_data['role']

            if 'username' in input_data:
                username = input_data['username']

            if username == None:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=400,
                               data='Bad request, username is missing'), 400

            target_account = Account.query.filter(Account.username == username).first()

            if target_account:

                if not can_account_write_group(account=account, group=group):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to group'), 403

                accountGroup = AccountGroup(id=str(uuid.uuid4()), 
                                            role_type=GroupRoleType[role], 
                                            account_id=target_account.id, 
                                            group_id=group.id)
                db.session.add(accountGroup)
                db.session.commit()
                return jsonify(accountGroup.to_dict()), 201
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=404,
                               data='Target account not found'), 404
        else:
            if not can_account_read_group(account=account, group=group):
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=403,
                               data='Account not authorized to read this group'), 403
            return jsonify([ag.account.username for ag in AccountGroup.query.filter(AccountGroup.group_id == group.id)])
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Group {0} not found'.format(id)), 404


@app.route('/groups/<id>/accounts/<username>', methods=['DELETE'])
@require_oauth()
def group_account(id, username):
    group = Group.query.filter(or_(Group.id == id, Group.name == id),
                                   Group.parent_id == current_token.account.group_id).first()
    if group:
        account = Account.query.filter(Account.id == current_token.account.id).first()
        target_account = Account.query.filter(Account.username == username).first()
        if target_account:

            target_account_groups = AccountGroup.query.filter(AccountGroup.account_id == target_account.id, AccountGroup.group_id == group.id)
            if request.method == 'DELETE':

                if not can_account_write_group(account=account, group=group):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to group'), 403
                
                for tg in target_account_groups:
                    db.session.delete(tg)
                
                db.session.commit()
                return jsonify(isError=False,
                               message="Success",
                               statusCode=200,
                               data='removed {0} from {1}'.format(username, group.name)), 200
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=400,
                               data='Bad request'), 400
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=404,
                           data='Account {0} not found'.format(username)), 404
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='Group {0} not found'.format(id)), 404
