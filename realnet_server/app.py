from flask import Flask
from .config import Config

cfg = Config()

app = Flask(__name__)