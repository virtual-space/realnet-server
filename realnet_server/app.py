from flask import Flask
from flask_migrate import Migrate

from .models import db

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'

db.init_app(app)

Migrate(app, db)


class App:

    @classmethod
    def app(cls):
        return app

    @classmethod
    def upgrade(cls):
        with app.app_context():
            from flask_migrate import upgrade as _upgrade
            _upgrade()
