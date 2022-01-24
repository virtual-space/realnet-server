from pynecone import Shell, ProtoCmd
import os
from realnet_server import app
from .models import db, initialize_server
from .config import Config

from dotenv import *

path = os.path.join(os.getcwd(), ".env")
if os.path.exists(path):
    load_dotenv(dotenv_path=path)


class Serve(ProtoCmd):

    def __init__(self):
        super().__init__('serve',
                         'start realnet server')

    def add_arguments(self, parser):
        parser.add_argument('--item', help='specify the name of the item to be served, default is root home folder')

    def run(self, args):
        cfg = Config()
        if args.item:
            app.config['ROOT_ITEM'] = args.item
        app.run(cfg.get_server_host(), cfg.get_server_port())


class Upgrade(ProtoCmd):

    def __init__(self):
        super().__init__('upgrade',
                         'upgrade realnet server')

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
        parser.add_argument('--uri', help='specify the tenant uri', default=os.getenv('REALNET_URI'))
        parser.add_argument('--redirect_uri', help='specify the tenant redirect uri', default=os.getenv('REALNET_REDIRECT_URI'))

    def run(self, args):
        with app.app_context():
            db.create_all()
            initialize_server(args.name, args.username, args.email, args.password, args.uri, args.redirect_uri)


class RealnetServer(Shell):

    def __init__(self):
        super().__init__('realnet-server')

    def get_commands(self):
        return [Serve(), Upgrade(), Initialize(), Migrate()]

    def add_arguments(self, parser):
        pass

    def get_help(self):
        return 'realnet server'