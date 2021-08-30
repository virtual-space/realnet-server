from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, Group, GroupRoleType, Account, AccountGroup, create_account
from sqlalchemy import or_


def can_account_create_account(account):
    for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                  AccountGroup.account_id == account.id):
        if accountGroup.role_type == GroupRoleType.root or accountGroup.role_type == GroupRoleType.admin:
            return True

    return False


def can_account_read_accounts(account, group):
    if account.group_id == group.id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root or accountGroup.role_type == GroupRoleType.admin:
                return True

    return False


def can_account_write_accounts(account, group):
    if account.group_id == group.id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root or accountGroup.role_type == GroupRoleType.admin:
                return True

    return False


def can_account_delete_accounts(account, group):
    if account.group_id == group.id:
        for accountGroup in AccountGroup.query.filter(AccountGroup.group_id == account.group_id,
                                                      AccountGroup.account_id == account.id):
            if accountGroup.role_type == GroupRoleType.root or accountGroup.role_type == GroupRoleType.admin:
                return True

    return False

@app.route('/accounts', methods=('GET', 'POST'))
@require_oauth()
def accounts():
    if request.method == 'POST':
        request.on_json_loading_failed = lambda x: print('json parsing error: ', x)
        input_data = request.get_json(force=True, silent=False)
        if input_data:
            input_username = input_data['username']
            input_password = input_data['password']
            input_type = input_data['type']
            input_role = input_data['role']
            input_email = input_data['email']

            if input_username and input_password and input_role and input_email:
                group = db.session.query(Group).filter(
                                   Group.id == current_token.account.group_id).first()

                if not can_account_create_account(current_token.account):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to group'), 403

                created = create_account(group.name,
                                         input_type,
                                         input_role,
                                         input_username,
                                         input_password,
                                         input_email)

                if created:
                    return jsonify(created.to_dict()), 201
                else:
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=400,
                                   data='Cannot create the account'), 400
            else:
                return jsonify(isError=True,
                               message="Failure",
                               statusCode=402,
                               data='Bad request, missing username, password, group, email, type or role parameter'), 402
    else:
        if not can_account_read_accounts(account=current_token.account, group=current_token.account.group):
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=403,
                           data='Account not authorized to read accounts'), 403
        return jsonify([q.to_dict() for q in Account.query.filter(Account.group_id == current_token.account.group_id)])

@app.route('/accounts/<id>', methods=['GET', 'PUT', 'DELETE'])
@require_oauth()
def single_account(id):
    acc = Account.query.filter(or_(Account.id == id, Account.username == id),
                                   Account.group_id == current_token.account.group_id).first()
    if acc:
        group = Group.query.filter(Group.id == acc.group_id,
                                   Group.parent_id == current_token.account.group_id).first()
        if group:
            if request.method == 'PUT':

                if not can_account_write_accounts(account=current_token.account, group=group):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to write to group'), 403

                input_data = request.get_json(force=True, silent=False)

                if 'password' in input_data:
                    acc.set_password(input_data['password'])
                    db.session.commit()

                return jsonify(acc.to_dict())

            elif request.method == 'DELETE':

                if not can_account_delete_accounts(account=current_token.account, group=group):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to delete this account'), 403

                db.session.delete(acc)
                db.session.commit()

                return jsonify(isError=False,
                               message="Success",
                               statusCode=200,
                               data='deleted account {0}'.format(id)), 200
            else:
                if not can_account_read_accounts(account=current_token.account, group=group):
                    return jsonify(isError=True,
                                   message="Failure",
                                   statusCode=403,
                                   data='Account not authorized to read this account'), 403
                return jsonify(acc.to_dict())
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=404,
                           data='group {0} not found'.format(acc.group_id)), 404

    return jsonify(isError=True,
                   message="Failure",
                   statusCode=404,
                   data='account {0} not found'.format(id)), 404

