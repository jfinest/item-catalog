from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask import Flask
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup2 import Base, Category, Book, User
from random import randint

#Importing for login_session
from flask import session as login_session
import random, string

#importing for OAuth
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
from flask import make_response
import requests

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

app = Flask(__name__)

engine = create_engine('sqlite:///books.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


#route for login
@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    #print "The current session state is %s" % login_session['state']
    return render_template('login.html', STATE=state)


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
        response = make_response(json.dumps('Current user is already connected.'),
                                 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['credentials'] = credentials
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
    output += '<h1>Welcome, '
    output += login_session['username']
    output += '!</h1>'
    output += '<img src="'
    output += login_session['picture']
    output += ' " style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;"> '
    flash("you are now logged in as %s" % login_session['username'])
    print "done!"
    return output


@app.route('/gdisconnect')
def gdisconnect():
	#disconnecting user
	credentials = login_session.get('credentials')
	if credentials is None:
		response = make_response(json.dumps('Current user not connected.'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	#revoking current token 
	access_token = credentials.access_token
	url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' %access_token
	h = httplib2.Http()
	result = h.request(url, 'GET')[0]
	if result['status'] == '200':
		del login_session['credentials']
		del login_session['gplus_id']
		del login_session['username']
		del login_session['email']
		del login_session['picture']

		response = make_response(json.dumps('Successfully disconnected'), 200)
		response.headers['Content-Type'] = 'application/json'
		return response
	else:
		response = make_response( json.dumps('Failed to revoke token for a given user.'), 400)
		response.headers['Content-Type'] = 'application/json'
		return response

@app.route('/')
@app.route('/book/')
def bookList():
  categories = session.query(Category).all()
  if 'username' not in login_session:
    return render_template('publicbooklist.html', categories=categories)
  else:
    return render_template('booklist.html', categories=categories)

@app.route('/book/<category_name>/JSON')
def categoryListJSON(category_name):
	selectedCategory = session.query(Book).filter_by(category_name=category_name).all()
	return jsonify(BookLists=[i.serialize for i in selectedCategory])

@app.route('/book/<category_name>/<book_view>/JSON')
def selectedBookJSON(category_name, book_view):
	selectedBook = session.query(Book).filter_by(title=book_view).one()
	return jsonify(BookSelected=selectedBook.serialize)

@app.route('/book/<category_name>/')
def selectedCategoryList(category_name):
  # name = session.query(Category).filter_by(id=categoryId).one()
  selectedCategory = session.query(Book).filter_by(category_name=category_name).all()
  if 'username' not in login_session:
    return render_template('publiccategorylist.html', selectedCategory=selectedCategory)
  else:
    return render_template('categorylist.html', selectedCategory=selectedCategory, user=getUserID(login_session['email']))


@app.route('/book/<category_name>/<book_view>/')
def viewSelectedBook(category_name, book_view):
  bookSelected = session.query(Book).filter_by(title=book_view).one()
  if 'username' not in login_session:
    return render_template('publicbookview.html', bookSelected=bookSelected)
  else:
    return render_template('bookview.html', bookSelected=bookSelected, user=getUserID(login_session['email']))

@app.route('/book/new/', methods=['GET', 'POST'])
def newBook():
  if 'username' not in login_session:
    return redirect('/login')
  if request.method == 'POST':
  	number = randint(6,12500)
  	newbook = Book(title=request.form['title'], author=request.form['author'], description=request.form['description'], category_name=request.form['category'], user_id= login_session['user_id'])
  	session.add(newbook)
  	# flash('New Book %s Successfully Created' % newBook.title)
  	session.commit()

	return redirect(url_for('bookList'))

  else:
  	return render_template('newbook.html')

@app.route('/book/<book_for_edit>/edit/', methods=['GET', 'POST'])
def editBook(book_for_edit):
	if 'username' not in login_session:
		return redirect('/login')
	editedBook = session.query(Book).filter_by(title=book_for_edit).one()
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
		# flash('Book Successfully Edited')
		session.commit()
		return redirect(url_for('bookList'))

	else:
	  return render_template(
          'editBook.html', editedBook=editedBook)


@app.route('/book/<book_to_delete>/delete/', methods=['GET', 'POST'])
def deleteBook(book_to_delete):
	if 'username' not in login_session:
		return redirect('/login')
	deletingBook = session.query(Book).filter_by(title=book_to_delete).first()
	if request.method == 'POST':
		session.delete(deletingBook)
		# flash('%s Successfully Deleted' % deletingBook.name)
		session.commit()
		return redirect(url_for('bookList'))
	else:
		return render_template('deletebook.html', book_to_delete=deletingBook)

def createUser(login_session):
  newUser = User(name = login_session['username'], email = login_session['email'], picture = login_session['picture'])
  session.add(newUser)
  session.commit()
  user = session.query(User).filter_by(email = login_session['email']).one()
  return user.id

def getUserInfo(user_id):
  user = session.query(User).filter_by(id = user_id).one()
  return user

def getUserID(email):
  try:
    user = session.query(User).filter_by(email = email).one()
    return user.id
  except:
    return None

if __name__ == '__main__':
    app.debug = True
    app.secret_key = 'super_secret_key'
    app.run(host='0.0.0.0', port=5000)