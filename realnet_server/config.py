import os
from dotenv import *

path = os.path.join(os.getcwd(), ".env")
if os.path.exists(path):
    load_dotenv(dotenv_path=path)

class Config:

    def get_database_url(self):
        return 'postgresql://{0}:{1}@{2}:{3}/{4}'.format(os.getenv('REALNET_DB_USER'),
                                                         os.getenv('REALNET_DB_PASS'),
                                                         os.getenv('REALNET_DB_HOST'),
                                                         os.getenv('REALNET_DB_PORT'),
                                                         os.getenv('REALNET_DB_NAME'))

    def get_server_host(self):
        return os.getenv('REALNET_SERVER_HOST')

    def get_server_port(self):
        return os.getenv('REALNET_SERVER_PORT')

    def get_storage(self):
        return {'type': os.getenv('REALNET_STORAGE_TYPE'),
                'path': os.getenv('REALNET_STORAGE_PATH')}
