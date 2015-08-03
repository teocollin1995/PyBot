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
import requests as req
TOKEN= '50177117:AAEL3w8LlTI8bjoBIkC057at0jnZti75lcY'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'
document = """
TBA
"""

class ChatInfo:
    def __init__(self, chat_id, group_chat = False):
        self.chat_id = chat_id
        self.group = group_chat
        self.members = dict([('admin',True)])
        self.code = code.InteractiveConsole()
    def clear(self):
        self.code = code.InteractiveConsole()
    def is_user(self, user):
        return user in self.members.keys()
    def add_user(self, user):
        self.members[user] = False
    def change_user_usage(self,user):
        self.members[user] = True
    
        
        
    
        

app = Flask(__name__)

global_code_dict = dict() #dict of chatInfos




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
    #things present in all messages that we want to process:
    
    message = body['message']
    fr = message.get('from')
    chat = message['chat']
    chat_id = chat['id']
    message_id = message.get('message_id')
    date = message.get('date')
    
    #at this point we can define our reply function
    
    def give_response(chat_id, msg):
        resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
            'chat_id': str(chat_id),
            'text': msg,
            'disable_web_page_preview': 'true',
            'reply_to_message_id': str(message_id),
        })).read()
    
    #things that are variable in the mssage
    #Atext will remain none if it is a group message
    atext = None
    atext = message.get('text')
    if atext == None:
        # it is a group message or something we don't like'
        atext = message.get(u'new_chat_participant') #tis a new message from a group.
        if atext != None:
            global_code_dict[chat_id] = ChatInfo(chat_id, group_chat = True)
            give_response(chat_id, document)
            resp = Response(r, status=200)
            return resp
        else:
            atext = message.get('left_chat_participant')
            if atext != None:
                global_code_dict[chat_id].clear()
                resp = Response(r, status=200)
                return resp
            else:
                logging.info("Included non-text content")
                give_response(chat_id, "Action not allowed, ass")
                resp = Response(r, status=200)
                return resp
    
    #ensure that if we pass this point, a chat object exists
    if chat_id not in global_code_dict.keys():
        global_code_dict[chat_id] = ChatInfo(chat_id)
                
    #ensure that if we pass this point, the user has been initalized
    if not global_code_dict[chat_id].is_user(fr):
        global_code_dict[chat_id].add_user(fr)
        
    

    
    #deal with special chars:
    btext = atext.rstrip("\\n")
    ctext = string.replace(btext, "\\t", '\t')
    text = string.replace(ctext, "\\n", '\n')
    #this is sloppy, fix it
    logging.info("text:")
    logging.info(text)
    # we can now define process command
    def process_command(cmd):
        f = StringIO()
        g = StringIO()
        executed = None
        with redirect_stdout(f):
            with redirect_stderr(g):
                executed = global_code_dict[chat_id].code.push(cmd)
                logging.info("Executed command with result: {}".format(str(executed)))
                

        if executed == False:
            cmd_res = "\"" + f.getvalue() + g.getvalue() + "\""
            logging.info("cmd result:")
            logging.info(cmd_res)
            global_code_dict[chat_id].code.resetbuffer()
            give_response(chat_id, cmd_res);
        else:
            logging.info("Waiting for further input")
            give_response(chat_id, "Processed command:\n{}".format(cmd))
            
        
        
    if text[0] == '/':
        if text == '/start':
            give_response(chat_id, "Ready. Please input command. Type /clear to clear enviro")
        elif text == '/clear':
            global_code_dict[chat_id].clear()
        elif text[0:2] == '/t':
            text = "\t" + text[2:]
            logging.info("indent parsed")
            process_command(text)
        elif text[0:3] == '/py':
            global_code_dict[chat_id].change_user_usage(fr)
            give_response(chat_id, "Toggled python input mode")
            resp = Response(r, status=200)
            return resp
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
