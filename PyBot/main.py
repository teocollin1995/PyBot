import string
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
        

    urlfetch.set_default_fetch_deadline(60)
    r = request.get_json()
    logging.info("raw request:")
    logging.info(r)
    body = r
    #get items:
    update_id = body['update_id']
    message = body['message']
    fr = message.get('from')
    chat = message['chat']
    chat_id = chat['id']
    message_id = message.get('message_id')
    date = message.get('date')
    atext = message.get('text')
    def give_response(chat_id, msg):
        resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
            'chat_id': str(chat_id),
            'text': msg,
            'disable_web_page_preview': 'true',
            'reply_to_message_id': str(message_id),
        })).read()
    try:
        btext = atext.rstrip("\n")
    except AttributeError:
        logging.info("Included non-text content")
        give_response(chat_id, "Action not allowed, ass")
        resp = Response(r, status=200)
        return resp
    
    #deal with special chars:
    text = string.replace(btext, "\\t", '\t')
    logging.info("text:")
    logging.info(text)
    
    

            
    
    def process_command(cmd):
        f = StringIO()
        g = StringIO()
        executed = None
        with redirect_stdout(f):
            with redirect_stderr(g):
                executed = global_code_dict[chat_id].push(cmd)
                logging.info("Executed command with result: {}".format(str(executed)))
                

        if executed == False:
            cmd_res = "\"" + f.getvalue() + g.getvalue() + "\""
            logging.info("cmd result:")
            logging.info(cmd_res)
            global_code_dict[chat_id].resetbuffer()
            give_response(chat_id, cmd_res);
        else:
            logging.info("Waiting for further input")
            give_response(chat_id, "Processed command:\n{}".format(cmd))
            
        


    

                        

    
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
        elif text[0:2] == '/t':
            text = "\t" + text[2:]
            logging.info("indent parsed")
            process_command(text)
        elif text == '/e':
            executed = global_code_dict[chat_id].push('\n')
            give_response(chat_id, "Terminated input: {}".format(str(executed)))
            resp = Response(r, status=200)
            return resp
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
    else: # make this into a function
        process_command(text)
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
