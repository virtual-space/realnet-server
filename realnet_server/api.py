from pynecone import Command
import uuid
from realnet_server import app
from .models import db, Authenticator, AuthenticatorType, Account, initialize
from .config import Config

class Api(Command):

    def __init__(self):
        super().__init__("api")

    def run(self, args):
        cfg = Config.init()
        if args.action == 'start':
            app.run(cfg.get_server_host(), cfg.get_server_port())
        elif args.action == 'upgrade':
            with app.app_context():
                from flask_migrate import upgrade as _upgrade
                _upgrade()
        elif args.action == 'migrate':
            with app.app_context():
                from flask_migrate import migrate as _migrate
                _migrate()
        elif args.action == 'create':
            with app.app_context():
                db.create_all()
                initialize()


    def add_arguments(self, parser):
        parser.add_argument('action', choices=['start', 'upgrade', 'migrate', 'create'], default='start', const='start', nargs='?', help='specify what to do with the server')
        parser.add_argument('--port', help='specify the port on which to run', default='8080', const='8080', nargs='?')

    def get_help(self):
        return 'relanet api server'