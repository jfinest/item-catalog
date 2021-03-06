from flask import Flask, render_template, request
from flask import redirect, url_for, flash, jsonify
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import desc
from database_setup2 import Base, Category, Book, User
from random import randint

# Importing for login_session
from flask import session as login_session
import random
import string

# importing for OAuth
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests
from functools import wraps


CLIENT_ID = json.loads(open('client_secrets.json',
                            'r').read())['web']['client_id']


app = Flask(__name__)


engine = create_engine('sqlite:///books.db')
Base.metadata.bind = engine


DBSession = sessionmaker(bind=engine)
session = DBSession()


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' not in login_session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function


# route for login
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    return render_template('login.html', STATE=state)


# Following method is used to get login info from google
@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # Obtain authorization code
    code = request.data

    try:
        # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."), 401)
        print "Token's client ID does not match app's."
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_credentials = login_session.get('credentials')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_credentials is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
                                'Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']

    user_id = getUserID(login_session['email'])
    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1> &nbsp &nbsp &nbsp Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '&nbsp &nbsp &nbsp &nbsp <img src="'
    output += login_session['picture']
    output += """  "style = "width: 300px; height: 300px;border-radius:
                   150px;-webkit-border-radius:
                   150px;-moz-border-radius: 150px;"> """
    return output


# This method will allow for logging out
@app.route('/gdisconnect')
def gdisconnect():
	# disconnecting user
    credentials = login_session.get('credentials')
    if credentials is None:
        response = make_response(json.dumps(
                               'Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # revoking current token
    access_token = credentials
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        del login_session['credentials']
        del login_session['gplus_id']
        del login_session['username']
        del login_session['email']
        del login_session['picture']

        response = make_response(json.dumps(
                               'Successfully disconnected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
                              'Failed to revoke token for a given user.'), 400)
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/')
@app.route('/book/')
def bookList():
    recent = session.query(Book).order_by(desc(Book.id)).limit(10)
    categories = session.query(Category).all()
    if 'username' not in login_session:
        return render_template('publicbooklist.html',
                               categories=categories,
                               recent=recent)
    else:
        return render_template('booklist.html',
                               categories=categories,
                               recent=recent)


@app.route('/book/<path:category_name>/JSON')
def categoryListJSON(category_name):
    selectedCategory = session.query(Book).filter_by(
                       category_name=category_name).all()
    return jsonify(BookLists=[i.serialize for i in selectedCategory])


@app.route('/book/<path:category_name>/<path:book_view>/JSON')
def selectedBookJSON(category_name, book_view):
    selectedBook = session.query(Book).filter_by(title=book_view).one()
    return jsonify(BookSelected=selectedBook.serialize)


@app.route('/book/<path:category_name>/')
def selectedCategoryList(category_name):
    selectedCategory = session.query(Book).filter_by(
                       category_name=category_name).all()
    if 'username' not in login_session:
        return render_template('publiccategorylist.html',
                               selectedCategory=selectedCategory,
                               category=category_name)
    else:
        return render_template('categorylist.html',
                               selectedCategory=selectedCategory,
                               user=getUserID(login_session['email']),
                               category=category_name)


@app.route('/book/<path:category_name>/<path:book_view>/')
def viewSelectedBook(category_name, book_view):
    bookSelected = session.query(Book).filter_by(title=book_view).one()
    if 'username' not in login_session:
        return render_template('publicbookview.html',
                               bookSelected=bookSelected)
    else:
        return render_template('bookview.html',
                               bookSelected=bookSelected,
                               user=getUserID(login_session['email']))


@app.route('/book/new/', methods=['GET', 'POST'])
@login_required
def newBook():
    categories = session.query(Category).all()
    if request.method == 'POST':
        newbook = Book(title=request.form['title'],
                       author=request.form['author'],
                       description=request.form['description'],
                       category_name=request.form['category'],
                       user_id=login_session['user_id'])
        session.add(newbook)
        session.commit()

        return redirect(url_for('bookList'))

    else:
        return render_template('newbook.html', categories=categories)


@app.route('/book/<path:book_for_edit>/edit/', methods=['GET', 'POST'])
@login_required
def editBook(book_for_edit):
    categories = session.query(Category).all()
    editedBook = session.query(Book).filter_by(title=book_for_edit).one()

    if editedBook.user_id != login_session['user_id']:
        return render_template('editBook.html',
                               editedBook=editedBook,
                               categories=categories,
                               user=getUserID(login_session['email']))

    if request.method == 'POST':
        if request.form['title']:
            editedBook.title = request.form['title']
        if request.form['author']:
            editedBook.author = request.form['author']
        if request.form['description']:
            editedBook.description = request.form['description']
        if request.form['category']:
            editedBook.category_name = request.form['category']
        session.add(editedBook)
        session.commit()
        return redirect(url_for('bookList'))

    else:
        return render_template('editBook.html',
                               editedBook=editedBook,
                               categories=categories,
                               user=getUserID(login_session['email']))


@app.route('/book/<path:book_to_delete>/delete/', methods=['GET', 'POST'])
@login_required
def deleteBook(book_to_delete):
    deletingBook = session.query(Book).filter_by(title=book_to_delete).first()

    if deletingBook.user_id != login_session['user_id']:
        return render_template('deleteBook.html',
                               book_to_delete=deletingBook,
                               user=getUserID(login_session['email']))

    if request.method == 'POST':
        session.delete(deletingBook)
        session.commit()
        return redirect(url_for('bookList'))
    else:
        return render_template('deletebook.html',
                               book_to_delete=deletingBook,
                               user=getUserID(login_session['email']))


def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


if __name__ == '__main__':
    app.debug = True
    app.secret_key = 'super_secret_key'
    app.run(host='0.0.0.0', port=5000)
