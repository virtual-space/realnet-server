__version__ = "0.0.1"

from flask import Flask
from flask_migrate import Migrate

from .config import Config

from .models import db

cfg = Config.init()

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = cfg.get_database_url()

db.init_app(app)

migrate = Migrate(app, db)

