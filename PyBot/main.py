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
import os
if os.environ.get('SERVER_SOFTWARE','').startswith('Dev'):
    from google.appengine.tools.dev_appserver import FakeFilex
    FakeFile.ALLOWED_MODES = frozenset(['a','r', 'w', 'rb', 'U', 'rU'])
import dill

TOKEN= '50177117:AAEL3w8LlTI8bjoBIkC057at0jnZti75lcY'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'
document = """
TBA
"""


class Member(ndb.Model):
    name = ndb.StringProperty()
    pymode = ndb.BooleanProperty()

class ChatInfo(ndb.Model):
    chat_id = ndb.StringProperty() #This will be our key
    group_chat = ndb.BooleanProperty()
    console = ndb.PickleProperty()
    members = ndb.StructuredProperty(Member, repeated=True)


app = Flask(__name__)

#global_code_dict = dict() #dict of chatInfos




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
    from_section = message.get('from')
    fr = from_section["username"] + from_section["last_name"] + from_section["first_name"]
    chat = message['chat']
    chat_id = str(chat['id'])
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
            group_chat = ChatInfo(id = chat_id)
            group_chat.group_chat = True
            group_chat.chat_id = chat_id
            group_chat.console = dill.dumps(code.InteractiveConsole())
            group_chat.members = [Member(name=fr,pymode=False)]
            group_chat.key.id()
            group_chat.push()
            give_response(chat_id, document)
            resp = Response(r, status=200)
            return resp
        else:
            atext = message.get('left_chat_participant')
            if atext != None:
                del_group_chat = ChatInfo.get_by_id(chat_id)
                del_group_chat.key.delete()
                resp = Response(r, status=200)
                return resp
            else:
                logging.info("Included non-text content")
                give_response(chat_id, "Action not allowed, ass")
                resp = Response(r, status=200)
                return resp
    
    #ensure that if we pass this point, a chat object exists
gerr = """ if chat_id not in global_code_dict.keys():
        global_code_dict[chat_id] = ChatInfo(chat_id)
                
    #ensure that if we pass this point, the user has been initalized
    if not global_code_dict[chat_id].is_user(fr):
        global_code_dict[chat_id].add_user(fr)
        #allow user to start sending code immeditately if they are not starting in a group chat
        if not global_code_dict[chat_id].group_chat:
            global_code_dict[chat_id].change_user_usage(fr)

    
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
            
        
    #last bit of logic for deciding what to do with the text
    pymod = global_code_dict[chat_id].python_mode(fr)
    logging.info("python mode is {}".format(pymod))
    if text[0] == '/':
        #check if they want to toggle python mode
        if text[0:3] == '/py':
            global_code_dict[chat_id].change_user_usage(fr)
            give_response(chat_id, "Toggled python input mode to {}".format(global_code_dict[chat_id].python_mode(fr)))
            resp = Response(r, status=200)
            return resp
            #check if they are in python mode to start with
        elif not pymod:
            logging.info("Discarding input")
            resp = Response(r, status=200) #discard if they are not in python mode
            return resp
        elif text == '/start': #give document
            give_response(chat_id, document)
        elif text == '/clear': #clear enviroment
            global_code_dict[chat_id].clear()
        elif text[0:2] == '/t': #depricated:
            text = "\t" + text[2:]
            logging.info("indent parsed")
            process_command(text)
        elif text == '/e': #finish a multiline input
            executed = global_code_dict[chat_id].push('\n')
            give_response(chat_id, "Terminated input: {}".format(str(executed)))
            resp = Response(r, status=200)
            return resp
        else:
            give_response(chat_id, "Action not allowed, ass!")
    #assuming there are no commands, let's check for any imports that we might not like
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
        process_command(text) #finally, do something

    resp = Response(r, status=200) #say that something happened
    return resp"""
        
    

    
    
    


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
