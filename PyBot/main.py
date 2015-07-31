import json
import logging
import urllib
import urllib2

from google.appengine.api import urlfetch
from google.appengine.ext import ndb
import webapp2

TOKEN= '50177117:AAGCMNPVi73DLAf-1hOnx6T247hfwG0hReM'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'
