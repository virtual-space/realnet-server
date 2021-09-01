import os
from dotenv import *

from .models import BlobType

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

    def get_storage_type(self):
        return BlobType[os.getenv('REALNET_STORAGE_TYPE')]

    def get_storage_path(self):
        return os.getenv('REALNET_STORAGE_PATH')

    def get_s3_region(self):
        return os.getenv('REALNET_STORAGE_S3_REGION')

    def get_s3_bucket(self):
        return os.getenv('REALNET_STORAGE_S3_BUCKET')

    def get_s3_key(self):
        return os.getenv('REALNET_STORAGE_S3_KEY')

    def get_s3_secret(self):
        return os.getenv('REALNET_STORAGE_S3_SECRET')

    def get_app_secret(self):
        return os.getenv('REALNET_APP_SECRET')

    def get_jwt_key(self):
        return os.getenv('REALNET_JWT_KEY')

    def get_jwt_issuer(self):
        return os.getenv('REALNET_JWT_ISSUER')
