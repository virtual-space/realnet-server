from flask import request, jsonify
from realnet_server import app
from .auth import require_oauth
from .models import Type


@app.route('/types', methods=('GET', 'POST'))
def types():
    if request.method == 'POST':
        return jsonify([q.to_dict() for q in Type.query.all()])
    else:
        return jsonify([q.to_dict() for q in Type.query.all()])