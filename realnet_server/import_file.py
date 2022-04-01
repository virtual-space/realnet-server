from flask import request, jsonify
from authlib.integrations.flask_oauth2 import current_token
from realnet_server import app
from .auth import require_oauth
from .models import db, Type, Instance, Group, Account, AccountGroup, GroupRoleType, import_items
from sqlalchemy import or_
import uuid

import csv
import json
import codecs
import mimetypes

@app.route('/import', methods=['POST'])
@require_oauth()
def import_file():
    infile = request.files['import']
    if not infile:
        return jsonify(isError=True,
                               message="Failure",
                               statusCode=402,
                               data='Bad request'), 402
    mimetype = mimetypes.guess_type(infile.filename)[0]
    print(mimetype)
    if mimetype =='application/vnd.ms-excel':
        stream = codecs.iterdecode(infile.stream, 'utf-8')
        items = []
        results = []
        for row in csv.reader(stream, dialect=csv.excel):
            if row:
                items.append(row)
        # print(data)
        if items:
            results = import_items(db, items, current_token.account.id, current_token.account.group_id)
        return jsonify(results), 201
    else:
        return jsonify(isError=True,
                               message="Failure",
                               statusCode=400,
                               data='Unsupported mime type {}'.format(mimetype)), 400
