FROM python:3.7-slim

WORKDIR /app

ADD realnet-server ./realnet-server
COPY setup.py ./
COPY LICENSE ./
COPY README.md ./
COPY runner ./
RUN python setup.py install

CMD [ "./runner" ]