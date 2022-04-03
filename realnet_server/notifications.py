from flask import request, jsonify
from realnet_server import app
from .auth import require_oauth


@app.route('/notifications', methods=('GET'))
@require_oauth()
def notifications():
    if request.method == 'GET':
        return jsonify([]), 200











