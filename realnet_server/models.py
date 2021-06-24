import enum
import uuid
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

from authlib.integrations.sqla_oauth2 import (
    OAuth2ClientMixin,
    OAuth2AuthorizationCodeMixin,
    OAuth2TokenMixin,
)


class AuthenticatorType(enum.Enum):
    password = 1
    oauth = 2


db = SQLAlchemy()

# https://stackoverflow.com/questions/52723239/spatialite-backend-for-geoalchemy2-in-python
# https://flask-sqlalchemy.palletsprojects.com/en/2.x/queries/

class Authenticator(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(40))
    type = db.Column(db.Enum(AuthenticatorType))
    client_id = db.Column(db.String(128))
    client_secret = db.Column(db.String(128))

class AccountType(enum.Enum):
    person = 1
    thing = 2

class Account(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.Enum(AccountType))
    username = db.Column(db.String(40), unique=True)
    email = db.Column(db.String(254), unique=True)
    password_hash = db.Column(db.String(128))
    data = db.Column(db.JSON)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __str__(self):
        return self.username

# Define the Role data-model
class Role(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), unique=True)

# Define the AccountRole association table
class AccountRole(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    account_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    role_id = db.Column(db.String(36), db.ForeignKey('role.id', ondelete='CASCADE'), nullable=False)

class AclType(enum.Enum):
    public = 1
    group = 2
    user = 3

# Define the Acl data-model
class Acl(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    type = db.Column(db.Enum(AclType))
    name = db.Column(db.String(50))
    permission = db.Column(db.String(50))

# Define the Group data-model
class Group(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(50), unique=True)

# Define the AccountGroup association table
class AccountGroup(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    account_id = db.Column(db.String(36), db.ForeignKey('account.id', ondelete='CASCADE'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id', ondelete='CASCADE'), nullable=False)


class Token(db.Model, OAuth2TokenMixin):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')

class AuthorizationCode(db.Model, OAuth2AuthorizationCodeMixin):
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')

class App(db.Model, OAuth2ClientMixin):
    id = db.Column(db.String(36), primary_key=True)
    account_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    account = db.relationship('Account')
    data = db.Column(db.JSON)

class Type(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    attributes = db.Column(db.JSON)
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)

class Item(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    attributes = db.Column(db.JSON)
    type_id = db.Column(db.String(36), db.ForeignKey('type.id'), nullable=False)
    owner_id = db.Column(db.String(36), db.ForeignKey('account.id'), nullable=False)
    group_id = db.Column(db.String(36), db.ForeignKey('group.id'), nullable=False)

# Define the ItemAcl association table
class ItemAcl(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    item_id = db.Column(db.String(36), db.ForeignKey('item.id', ondelete='CASCADE'), nullable=False)
    acl_id = db.Column(db.String(36), db.ForeignKey('acl.id', ondelete='CASCADE'), nullable=False)

def initialize():
    # db.session.add(Authenticator(id=str(uuid.uuid4()), name='realnet', type=AuthenticatorType.password))
    admin_id = str(uuid.uuid4())
    db.session.add(Role(id=admin_id, name='admin'))
    account_id = str(uuid.uuid4())
    account = Account(id=account_id, type=AccountType.person, username='admin', email='admin@realnet.io')
    account.set_password('123456')
    db.session.add(account)
    db.session.add(AccountRole(id=str(uuid.uuid4()), account_id=account_id, role_id=admin_id))
    db.session.commit()

