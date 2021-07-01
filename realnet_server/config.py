import yaml
import os

DB_USER = 'backend'
DB_HOST = 'localhost'
DB_PASS = 'k0kic3'
DB_PORT = '5432'
DB_NAME = 'realnet'

class Config:
    def __init__(self, name, path):
        self.path = path
        self.full_path = os.path.join(path, name)
        self.data = {}

    def load(self):
        with open(self.full_path) as file:
            self.data = yaml.safe_load(file)

    def generate(self):
        print('*** Generating default config file ***')

        dict_file = {
                     # 'database': {'url': 'sqlite:///{0}'.format(os.path.join(self.path, 'realnet-server.db'))},
                     'database': {'url': 'postgresql://{0}:{1}@{2}:{3}/{4}'.format(DB_USER, DB_PASS, DB_HOST, DB_PORT, DB_NAME)},
                      'server': {'host': '0.0.0.0', 'port': '8080'},
                      'storage': {'type': 'local', 'path': os.path.join(os.getcwd(), 'storage')}}

        with open(self.full_path, 'w') as file:
            yaml.dump(dict_file, file)

    def get_database_url(self):
        return self.data['database']['url']

    def get_server_host(self):
        return self.data['server']['host']

    def get_server_port(self):
        return self.data['server']['port']

    def get_storage(self):
        return self.data['storage']

    @classmethod
    def init(cls, name='realnet-server.yml', path=os.getcwd()):
        cfg = Config(name, path)

        if not os.path.exists(cfg.full_path):
            cfg.generate()

        cfg.load()
        return cfg
