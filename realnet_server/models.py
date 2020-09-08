from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Admin(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))

class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128))