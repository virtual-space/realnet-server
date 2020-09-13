from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# https://stackoverflow.com/questions/52723239/spatialite-backend-for-geoalchemy2-in-python
# https://flask-sqlalchemy.palletsprojects.com/en/2.x/queries/
# https://flask-sqlalchemy.palletsprojects.com/en/2.x/models/

class Type(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    attributes = db.Column(db.JSON)


class Item(db.Model):
    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(128))
    attributes = db.Column(db.JSON)
    type_id = db.Column(db.String(36), db.ForeignKey('type.id'), nullable=False)