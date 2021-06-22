from flask_sqlalchemy import SQLAlchemy

from authlib.integrations.sqla_oauth2 import (
    OAuth2ClientMixin,
    OAuth2AuthorizationCodeMixin,
    OAuth2TokenMixin,
)

db = SQLAlchemy()

# https://stackoverflow.com/questions/52723239/spatialite-backend-for-geoalchemy2-in-python
# https://flask-sqlalchemy.palletsprojects.com/en/2.x/queries/

# class Authenticator(db.Model):
#    id = db.Column(db.String(36), primary_key=True)
#    data = db.Column(db.JSON)

class Account(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    username = db.Column(db.String(40), unique=True)

    data = db.Column(db.JSON)
    # authenticator_id = db.Column(db.String(36), db.ForeignKey('authenticator.id'), nullable=False)
    # authenticator = db.relationship('Authenticator')

    def check_password(self, password):
        pass

    def __str__(self):
        return self.username

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

