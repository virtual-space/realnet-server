__version__ = "0.0.4"

from flask import Flask
from flask_cors import CORS

from flask_migrate import Migrate

from flask_bootstrap import Bootstrap

from .config import Config

from .models import db, Account, Token

from .auth import config_oauth

import jinja2

import logging
logging.basicConfig(level=logging.DEBUG)

cfg = Config()

app = Flask(__name__)
CORS(app)
# import realnet_server.wsgi

app.secret_key = cfg.get_app_secret()
app.config['SQLALCHEMY_DATABASE_URI'] = cfg.get_database_url()
app.config['SQLALCHEMY_ECHO'] = True
app.config['GOOGLE_CLIENT_ID'] = ''
app.config['GOOGLE_CLIENT_SECRET'] = ''
app.config['BOOTSTRAP_SERVE_LOCAL'] = True


app.jinja_loader = jinja2.ChoiceLoader([
    app.jinja_loader,
    jinja2.PackageLoader(__name__) # in the same folder will search the 'templates' folder
])


db.init_app(app)

bootstrap = Bootstrap(app)

config_oauth(app)

migrate = Migrate(app, db)

migrate.init_app(app, db)


import realnet_server.oauth
import realnet_server.items
import realnet_server.types
import realnet_server.groups
import realnet_server.apps
import realnet_server.accounts
import realnet_server.authenticators
import realnet_server.tenants
import realnet_server.mobile
import realnet_server.import_file





