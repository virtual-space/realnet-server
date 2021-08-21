from pynecone import ProtoCmd, ProtoShell
import uuid
import os
from realnet_server import app
from .models import db, Authenticator, AuthenticatorType, Account, initialize_server
from .config import Config


class Start(ProtoCmd):

    def __init__(self):
        super().__init__('start',
                         'start api server')

    def add_arguments(self, parser):
        pass

    def run(self, args):
        cfg = Config.init()
        app.run(cfg.get_server_host(), cfg.get_server_port())


class Upgrade(ProtoCmd):

    def __init__(self):
        super().__init__('upgrade',
                         'upgrade api server')

    def add_arguments(self, parser):
        pass

    def run(self, args):
        with app.app_context():
            from flask_migrate import upgrade as _upgrade
            _upgrade()


class Migrate(ProtoCmd):

    def __init__(self):
        super().__init__('migrate',
                         'migrate api server')

    def add_arguments(self, parser):
        pass

    def run(self, args):
        with app.app_context():
            from flask_migrate import migrate as _migrate
            _migrate()


class Initialize(ProtoCmd):

    def __init__(self):
        super().__init__('initialize',
                         'initialize api server')

    def add_arguments(self, parser):
        parser.add_argument('--name', help='specify the tenant name', default=os.getenv('REALNET_NAME'))
        parser.add_argument('--username', help='specify the root username', default=os.getenv('REALNET_USERNAME'))
        parser.add_argument('--password', help='specify the root password', default=os.getenv('REALNET_PASSWORD'))
        parser.add_argument('--email', help='specify the root email', default=os.getenv('REALNET_EMAIL'))

    def run(self, args):
        with app.app_context():
            db.create_all()
            initialize_server(args.name, args.username, args.email, args.password)


class Api(ProtoShell):

    def __init__(self):
        super().__init__('api', 
                         [Start(), Upgrade(), Initialize(), Migrate()], 
                         'realnet api server' )
