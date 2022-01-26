from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, Item
import uuid


@app.route('/people', methods=('GET'))
@require_oauth()
def people():
    if request.method == 'GET':
        item = Item.query.filter(Item.id == current_token.account.id)
        if item:
            return jsonify(item.to_dict()), 200
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=404,
                           data='Person not found'), 404










