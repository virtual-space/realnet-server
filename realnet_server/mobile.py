from flask import request, jsonify

from .auth import require_oauth
from authlib.integrations.flask_oauth2 import current_token

from realnet_server import app

from .models import Item

@app.route('/people', methods=('GET', 'POST'))
@require_oauth()
def people():
    if request.method == 'POST':
        pass
    else:
        person = Item.query.filter(Item.id == current_token.account.id).first()
        if person:
            return jsonify(person.to_dict())
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=404,
                           data='person {0} not found'.format(id)), 404

@app.route('/people/<id>')
@require_oauth()
def person(id):
    item = Item.query.filter(Item.id == id).first()
    if item:
        return jsonify(item.to_dict())
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='person {0} not found'.format(id)), 404


@app.route('/locations/entity/<id>')
@require_oauth()
def entity_locations(id):
    item = Item.query.filter(Item.id == id).first()
    if item:
        return jsonify(item.to_dict())
    else:
        return jsonify(isError=True,
                       message="Failure",
                       statusCode=404,
                       data='item {0} not found'.format(id)), 404

@app.route('/notifications')
@require_oauth()
def notifications():
    return jsonify([])

@app.route('/things')
@require_oauth()
def things():
    return jsonify([])

@app.route('/entities')
@require_oauth()
def entities():
    return jsonify([])

@app.route('/topics/mytopics')
@require_oauth()
def topics_mytopics():
    return jsonify([])