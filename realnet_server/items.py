from realnet_server import app
from flask import request, jsonify


@app.route('/items', methods=['GET'])
def get_items():
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data=request.args), 200


@app.route('/items', methods=['POST'])
def create_item():
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data=request.json), 200


@app.route('/items/<id>', methods=['GET'])
def get_item(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='get_item {0}'.format(id)), 200


@app.route('/items/<id>', methods=['PUT'])
def put_item(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='put_item {0}'.format(id)), 200


@app.route('/items/<id>', methods=['DELETE'])
def delete_item(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='delete_item {0}'.format(id)), 200


@app.route('/items/<id>/data', methods=['GET'])
def get_item(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='get_item_data {0}'.format(id)), 200


@app.route('/items/<id>/data', methods=['PUT'])
def put_item(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='put_item_data {0}'.format(id)), 200


@app.route('/items/<id>/data', methods=['DELETE'])
def delete_item(id):
    return jsonify(isError=False,
                       message="Success",
                       statusCode=200,
                       data='delete_item_data {0}'.format(id)), 200

