FROM python:3.7-slim

WORKDIR /app

ADD realnet_server ./realnet_server
COPY setup.py ./
COPY LICENSE ./
COPY README.md ./
COPY runner ./
RUN apt-get update && apt-get install -y gcc python3-dev
RUN python setup.py install

CMD [ "./runner" ]