from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, Item, Type, Acl, AclType
import uuid


@app.route('/profile', methods=['GET'])
@require_oauth()
def profile():
    if request.method == 'GET':
        item = Item.query.filter(Item.id == current_token.account.id).first()
        if item:
            return jsonify(item.to_dict()), 200
        else:
            return jsonify(isError=True,
                           message="Failure",
                           statusCode=404,
                           data='Person not found'), 404


@app.route('/public/profile', methods=['GET'])
def public_profile():
    if request.method == 'GET':
        type = db.session.query(Type).filter(Type.name == 'PublicApps').first()
        if type:
            item = Item.query.filter(Item.type_id == type.id, Item.acls.any(Acl.type == AclType.public)).first()
            if item:
                return jsonify(item.to_dict()), 200
            
    return jsonify( isError=True,
                    message="Failure",
                    statusCode=404,
                    data='Person not found'), 404










