import time, uuid
from flask import Blueprint, request, session, url_for
from flask import render_template, redirect, jsonify, abort
from werkzeug.security import gen_salt
from authlib.integrations.flask_client import OAuth
from loginpass import create_flask_blueprint
from loginpass import Twitter, GitHub, Google
from authlib.integrations.flask_oauth2 import current_token
from authlib.oauth2 import OAuth2Error
from .models import db, Account, App
from .auth import authorization, require_oauth
from realnet_server import app

oauth = OAuth(app)

backends = [Twitter, GitHub, Google]


@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        account = Account.query.filter_by(username=username).first()
        if not account:
            return redirect('/login')
        session['id'] = account.id
        return redirect('/')
    else:
        return render_template('login.html')
    # tpl = '<li><a href="/login/{}">{}</a></li>'
    # lis = [tpl.format(b.NAME, b.NAME) for b in backends]
    # return '<ul>{}</ul>'.format(''.join(lis))

@app.route('/settings')
def settings():
    account = current_user()
    return render_template('settings.html',account=account)

@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        account1 = Account.query.filter_by(username=username).first()
        account2 = Account.query.filter_by( email=email).first()
        if account1 or account2:
            return render_template('register.html')
        else:
            account = Account(id=str(uuid.uuid4()), username=username, email=email)
            account.set_password(password)
            db.session.add(account)
            db.session.commit()
            session['id'] = account.id
            print('post', session['id'])
            # if user is not just to log in, but need to head back to the auth page, then go for it
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect('/')
    else:
        return render_template('register.html')

@app.route('/error')
def error():
    return render_template('error.html')

def handle_authorize(remote, token, user_info):
    return jsonify(user_info)


bp = create_flask_blueprint(backends, oauth, handle_authorize)
app.register_blueprint(bp, url_prefix='')

def current_user():
    if 'id' in session:
        uid = session['id']
        return Account.query.get(uid)
    return None

def split_by_crlf(s):
    return [v for v in s.splitlines() if v]

@app.route('/', methods=('GET', 'POST'))
def home():
    if request.method == 'POST':
        username = request.form.get('username')
        account = Account.query.filter_by(username=username).first()
        if not account:
            account = Account(id=username, username=username)
            db.session.add(account)
            db.session.commit()
        session['id'] = account.id
        print('post', session['id'])
        # if user is not just to log in, but need to head back to the auth page, then go for it
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect('/')
    account = current_user()
    print('get', account)
    if account:
        clients = App.query.filter_by(owner_id=account.id).all()
    else:
        clients = []

    return render_template('home.html', account=account, clients=clients)

@app.route('/logout')
def logout():
    del session['id']
    return redirect('/')

@app.route('/create_client', methods=('GET', 'POST'))
def create_client():
    user = current_user()
    if not user:
        return redirect('/')
    if request.method == 'GET':
        return render_template('create_client.html')

    client_id = gen_salt(24)
    client_id_issued_at = int(time.time())
    client = App(
        id=str(uuid.uuid4()),
        client_id=client_id,
        client_id_issued_at=client_id_issued_at,
        owner_id=user.id,
        group_id=user.group_id
    )

    form = request.form
    client_metadata = {
        "client_name": form["client_name"],
        "client_uri": form["client_uri"],
        "grant_types": split_by_crlf(form["grant_type"]),
        "redirect_uris": split_by_crlf(form["redirect_uri"]),
        "response_types": split_by_crlf(form["response_type"]),
        "scope": form["scope"],
        "token_endpoint_auth_method": form["token_endpoint_auth_method"]
    }
    client.set_client_metadata(client_metadata)

    if form['token_endpoint_auth_method'] == 'none':
        client.client_secret = ''
    else:
        client.client_secret = gen_salt(48)

    db.session.add(client)
    db.session.commit()
    return redirect('/')

@app.route('/oauth/authorize', methods=['GET', 'POST'])
def authorize():
    user = current_user()
    # if user log status is not true (Auth server), then to log it in
    if not user:
        return redirect(url_for('website.routes.home', next=request.url))
    if request.method == 'GET':
        try:
            grant = authorization.validate_consent_request(end_user=user)
        except OAuth2Error as error:
            return error.error
        return render_template('authorize.html', user=user, grant=grant)
    if not user and 'username' in request.form:
        username = request.form.get('username')
        user = Account.query.filter_by(username=username).first()
    if request.form['confirm']:
        grant_user = user
    else:
        grant_user = None
    return authorization.create_authorization_response(grant_user=grant_user)


@app.route('/oauth/token', methods=['POST'])
def issue_token():
    return authorization.create_token_response()


@app.route('/oauth/revoke', methods=['POST'])
def revoke_token():
    return authorization.create_endpoint_response('revocation')


@app.route('/api/me')
@require_oauth('profile')
def api_me():
    user = current_token.user
    return jsonify(id=user.id, username=user.username)

