from pynecone import Command
from flask import Flask

class Start(Command):

    def __init__(self):
        super().__init__("start")

    def run(self, args):
        app = Flask('realnet-server')

        @app.route('/')
        def hello_world():
            return 'Welcome anonymous, <a href="/private">Log in</a>'

        app.run('localhost', port=5000)