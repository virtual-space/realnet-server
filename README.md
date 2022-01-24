# realnet-server
## How to run on linux using pip (deployed version)

- Create a folder and go to it.
```
mkdir realnet-server
cd realnet-server
```
- The realnet-server will need a database to connect to. Instructions for how to create a local db will be included at the end.
- In the repo root folder create an .env file with the following content:
```
REALNET_SERVER_HOST='0.0.0.0'
REALNET_SERVER_PORT='8080'
REALNET_DB_USER='realnet'
REALNET_DB_HOST='localhost'
REALNET_DB_PASS='Q1w35rr!423421345fdsfgs'
REALNET_DB_PORT='5432'
REALNET_DB_NAME='realnet'
REALNET_STORAGE_TYPE='s3'
REALNET_STORAGE_PATH='\realnet-server\storage'
REALNET_STORAGE_S3_BUCKET='realnet-dev'
REALNET_STORAGE_S3_KEY='ddd'
REALNET_STORAGE_S3_SECRET='ggg'
REALNET_STORAGE_S3_REGION='us-east-1'
REALNET_NAME='public'
REALNET_USERNAME='admin'
REALNET_EMAIL='joe.blog@gmail.com'
REALNET_REDIRECT_URI='http://localhost:4200/callback'
```

- run command
```
chmod 700 .env
```

- run the following commands:
```
python3 -m venv venv
. ./venv/bin/activate
pip install realnet-server
```

- finally to start realnet server run the following command:
```
realnet-server serve
```
Choose from 'serve', 'upgrade', 'initialize', 'migrate'.

## How to run on linux from source:

- Clone out the repo
```
git clone https://github.com/virtual-space/realnet-server/realnet-server.git
```
- Go to the repo root folder 
```
cd realnet-server
```
- The realnet-server will need a database to connect to. Instructions for how to create a local db will be included at the end.
- In the repo root folder create an .env file with the following content:
```
REALNET_SERVER_HOST='0.0.0.0'
REALNET_SERVER_PORT='8080'
REALNET_DB_USER='realnet'
REALNET_DB_HOST='localhost'
REALNET_DB_PASS='Q1w35rr!423421345fdsfgs'
REALNET_DB_PORT='5432'
REALNET_DB_NAME='realnet'
REALNET_STORAGE_TYPE='s3'
REALNET_STORAGE_PATH='\realnet-server\storage'
REALNET_STORAGE_S3_BUCKET='realnet-dev'
REALNET_STORAGE_S3_KEY='ddd'
REALNET_STORAGE_S3_SECRET='ggg'
REALNET_STORAGE_S3_REGION='us-east-1'
REALNET_NAME='public'
REALNET_USERNAME='admin'
REALNET_EMAIL='joe.blog@gmail.com'
REALNET_REDIRECT_URI='http://localhost:4200/callback'
```
- run command
```
chmod 700 .env
```

- run the following commands:
```
python3 -m venv venv
. ./venv/bin/activate
python setup.py install
```
- finally to start realnet server run the following command:
```
realnet-server serve
```
Choose from 'serve', 'upgrade', 'initialize', 'migrate'.

# Running as a local development server

Run the following command before `realnet-server serve`. This disables the https requirement.
```
export AUTHLIB_INSECURE_TRANSPORT=1
```

If you have your own database, you should also run the following to initialize the database.
```
realnet-server initialize
```


# python setup.py install notes

You may need to manually install some dependencies. `python setup.py install` should tell you what is missing.

The Cryptography module takes a long time to compile.

Below is an incomplete list of installation instructions for dependencies. If you're not doing this on a fresh installation, you should run `python setup.py install` to see what you need first.

## Inside VENV
- Cryptography dependencies
```
pip install --upgrade pip
pip install setuptools-rust
```
## Outside VENV
- postgreSQL (pg_config is missing)
```
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get -y install postgresql
```
- c/c++ compilers (gcc/g++ is missing)
```
sudo apt update
sudo apt install build-essential
```
Optional Man pages
```
sudo apt-get install manpages-dev
```
To test the C & C++ compiler installations run these commands:
```
gcc --version
g++ --version
```

# Creating a database for realnet-server
The following section should be done on your windows terminal if you are using WSL2.

Install Docker: https://docs.docker.com/desktop/windows/install/
Install Kubernetes: Go to settings in docker -> kubernetes -> enable kubernetes.

Get helm 3.1.0 or above.
Create a postgresql container in docker using the bitnami distribution: https://github.com/bitnami/charts/tree/master/bitnami/postgresql
Run the following after installing helm.
```
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update
helm install realnet -f values.yaml bitnami/postgresql
```
This requires a values.yaml file to be in directory you use this command: You can get one from the bitnami github. You probably want to change from the default password and use a port that won't interfere with other databases on the system.

Replace password and port in the .env file with the password and port you used in values.yaml

Run `kubectl port-forward --namespace default svc/realnet-postgresql [port]:[port]` in a linux terminal. This allows connections from outside the container to reach the database.

Run in linux:
```
sudo docker ps -a
```
This will list the containers available in docker. Note the CONTAINER ID of the database you just created.
Run the following commands:
```
docker exec -u root -it [CONTAINER ID] bash
install_packages postgis
psql -U postgres
CREATE EXTENSION postgis;
```
Check version:
```
SELECT postgis_version();
```
This should produce the following.
```
---------------------------------------
 2.5 USE_GEOS=1 USE_PROJ=1 USE_STATS=1
(1 row)
```
Once the .env details have been updated to point at your local database, use `realnet-server initialize` to create the default database in your venv. This will also complain that there is no REALNET_PASSWORD. You will need to include one in the .env file, or add it to the initialize command via `--password`.

# Notes for MacOS

Build from sources:
1. brew install libyaml
2. pip install pyyaml
3. pip install cython
4. brew install shapely
5. pip install geos
6. pip install cryptography
7. If you are having trouble installing psycopg2 by pointing it to where your openssl library is, ie:
env LDFLAGS="-I/opt/homebrew/Cellar/openssl@1.1/1.1.1m/include -L/opt/homebrew/Cellar/openssl@1.1/1.1.1m/lib" python setup.py install