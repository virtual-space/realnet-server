from realnet_server import app

@app.route('/types')
def types():
    return 'Hello World!'