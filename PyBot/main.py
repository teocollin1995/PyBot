import json
import logging
import urllib
import urllib2
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from flask import Flask

TOKEN= '50177117:AAGCMNPVi73DLAf-1hOnx6T247hfwG0hReM'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'

app = Flask(__name__)

@app.route('/me')
def display_me():
    urlfetch.set_default_fetch_deadline(60)
    return json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe')))


@app.route('/')
def hello():
    """Return a friendly HTTP greeting."""
    return 'Hello World!'


@app.errorhandler(404)
def page_not_found(e):
    """Return a custom 404 error."""
    return 'Sorry, Nothing at this URL.', 404


@app.errorhandler(500)
def application_error(e):
    """Return a custom 500 error."""
    return 'Sorry, unexpected error: {}'.format(e), 500
