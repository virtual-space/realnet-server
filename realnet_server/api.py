from pynecone import Command
import os

class Api(Command):

    def __init__(self):
        super().__init__("api")

    def run(self, args):
        if args.action == 'start':
            os.system('flask run')
        else:
            os.system('flask db upgrade')

    def add_arguments(self, parser):
        parser.add_argument('action', choices=['start', 'upgrade'], default='start', const='start', nargs='?', help='specify what to do with the server')
        parser.add_argument('--port', help='specify the port on which to run', default='8080', const='8080', nargs='?')

    def get_help(self):
        return 'relanet api server'