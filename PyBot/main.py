import json
import logging
import urllib
import urllib2
from google.appengine.api import urlfetch
from google.appengine.ext import ndb
from flask import Flask, jsonify, request, Response
import code
from StringIO import StringIO
import sys
from contextlib import contextmanager
TOKEN= '50177117:AAGVLewUdQ4t9ELxQ6nZlXyWzEsqha3wxHU'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'

app = Flask(__name__)

global_code_dict = dict()
#global_entery_dct = dict()

def agg():
    
    print "aggg!"

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
    body = r
    #get items:
    update_id = body['update_id']
    message = body['message']
    message_id = message.get('message_id')
    date = message.get('date')
    atext = message.get('text')
    text = atext.rstrip("\n")
    if '\t' in text:
        logging.info("had tab")
    logging.info("text:")
    logging.info(text)
    fr = message.get('from')
    chat = message['chat']
    chat_id = chat['id']
    

    def give_response(chat_id, msg):
            resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                'chat_id': str(chat_id),
                'text': msg.encode('utf-8'),
                'disable_web_page_preview': 'true',
                'reply_to_message_id': str(message_id),
            })).read()
            
        
            
    #from https://stackoverflow.com/questions/22425453/redirect-output-from-stdin-using-code-module-in-python
    @contextmanager
    def redirect_stdout(new_target):
        old_target, sys.stdout = sys.stdout, new_target # replace sys.stdout
        try:
            yield new_target # run some code with the replaced stdout
        finally:
            sys.stdout = old_target # restore to the previous value
    @contextmanager
    def redirect_stderr(new_target):
        old_target, sys.stderr = sys.stderr, new_target # replace sys.stdout
        try:
            yield new_target # run some code with the replaced stdout
        finally:
            sys.stderr = old_target # restore to the previous value
        

    
    if chat_id not in global_code_dict.keys():
        global_code_dict[chat_id] = code.InteractiveConsole()
        #global_code_dict[chat_id].runcode("import sys")
        #global_code_dict[chat_id].runcode("sys.stdout = open('{}', 'rw+')".format(str(chat_id) + "stdout"))
        #global_code_dict[chat_id].runcode("sys.stderr = open('{}', 'rw+')".format(str(chat_id) + "stderr"))
        
    if text[0] == '/':
        if text == '/start':
            give_response(chat_id, "Ready. Please input command. Type /clear to clear enviro")
        elif text == '/clear':
            del global_code_dict[chat_id]
        else:
            give_response(chat_id, "Action not allowed, ass!")
    elif 'import os' in text:
        give_response(chat_id, "Ass!")
    elif 'sys.' in text:
        give_response(chat_id, "Ass!")
    elif 'from os' in text:
        give_response(chat_id, "Ass!")
    elif 'from sys' in text:
        give_response(chat_id, "Ass!")
    elif 'import sys' in text:
        give_response(chat_id, "Ass!")
    else:
        f = StringIO()
        g = StringIO()
        executed = None
        with redirect_stdout(f):
            with redirect_stderr(g):
                executed = global_code_dict[chat_id].push(text)
                
        #global_code_dict[chat_id].runcode("sys.stdout.close()")
        #global_code_dict[chat_id].runcode("sys.stderr.close()")
        #out = open("{}".format(str(chat_id) + "stdout"), 'rw+')
        #err = open("{}".format(str(chat_id) + "stderr"), 'rw+')
        #cmd_res = out.read() + err.read()
        #out.seek(0)
        #err.seek(0)
        #out.truncate()
        #err.truncate()
        #out.close()
        #err.close()
        if executed == False:
            cmd_res = "\"" + f.getvalue() + g.getvalue() + "\""
            logging.info("cmd result:")
            logging.info(cmd_res)
            global_code_dict[chat_id].resetbuffer()

            if cmd_res and cmd_res != "": #not eq ""
                give_response(chat_id, cmd_res)
            else:
                give_response(chat_id, "Processed command:\n{}".format(text))

        else:
            give_response(chat_id, "Processed command:\n{}".format(text))

    resp = Response(r, status=200)
    return resp
        
    

    
    
    


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
