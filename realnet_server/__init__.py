__version__ = "0.0.1"

from flask import Flask
from flask_migrate import Migrate

from .config import Config

from .models import db, Account, Token

from realnet_core import ItemMemStore
from .auth import config_oauth

import jinja2

cfg = Config.init()

app = Flask(__name__)
app.secret_key = '!secret'
app.config['SQLALCHEMY_DATABASE_URI'] = cfg.get_database_url()

app.jinja_loader = jinja2.ChoiceLoader([
    app.jinja_loader,
    jinja2.PackageLoader(__name__) # in the same folder will search the 'templates' folder
])

db.init_app(app)

config_oauth(app)

migrate = Migrate(app, db)

migrate.init_app(app, db)

store = ItemMemStore()

import realnet_server.oauth
import realnet_server.items
import realnet_server.types




