import json
import logging
import urllib
import urllib2
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from flask import Flask, jsonify, request, Response

TOKEN= '50177117:AAGCMNPVi73DLAf-1hOnx6T247hfwG0hReM'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'

app = Flask(__name__)

@app.route('/me')
def display_me():
    urlfetch.set_default_fetch_deadline(60)
    return json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe')))

@app.route('/setwh')
def set_webhook():
    urlfetch.set_default_fetch_deadline(60)
    return json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': "https://pybot-1023.appspot.com/webhook"}))))

@app.route('/webhook', methods=["PUT", "POST"])
def wh():
    urlfetch.set_default_fetch_deadline(60)
    r = request.get_json()
    logging.info("raw request:")
    logging.info(r)
    Response(jsonify(r))
    body = r
    logging.info('request body:')
    logging.info(body)
    update_id = body['update_id']
    message = body['message']
    message_id = message.get('message_id')
    date = message.get('date')
    text = message.get('text')
    fr = message.get('from')
    chat = message['chat']
    chat_id = chat['id']
    
    resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
        'chat_id': str(chat_id),
        'text': text.encode('utf-8'),
        'disable_web_page_preview': 'true',
        'reply_to_message_id': str(message_id),
    })).read()
    


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
