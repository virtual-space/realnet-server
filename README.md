# realnet-server
## How to run on linux:

NEED TO ADD INSTRUCTIONS FOR INSTALLING AND CREATING A DOCKER SERVER

- Clone out the repo
```
git clone https://github.com/virtual-space/realnet-server/realnet-server.git
```
- Go to the repo root folder 
```
cd realnet-server
```
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
REALNET_NAME='root'
REALNET_USERNAME='admin'
REALNET_PASSWORD='fsdf7987f9sd87f89sdf789s'
REALNET_EMAIL='joe.blog@gmail.com'
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
realnet-server 
```
Choose from 'serve', 'upgrade', 'initialize', 'migrate'.

- python setup.py install notes

You may need to manually install some dependencies. `python setup.py install` should tell you what is missing.

The Cryptography module takes a long time to compile.

Below is an incomplete list of installation instructions for dependencies. If you're not doing this on a fresh installation, you should run `python setup.py install` to see what you need first.

- Inside VENV
```
pip install --upgrade pip
pip install setuptools-rust
```
- Outside VENV
postgreSQL (pg_config is missing)
```
sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt $(lsb_release -cs)-pgdg main" > /etc/apt/sources.list.d/pgdg.list'
wget --quiet -O - https://www.postgresql.org/media/keys/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get -y install postgresql
```
c/c++ compilers (gcc/g++ is missing)
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