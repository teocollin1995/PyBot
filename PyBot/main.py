import string
import json
import logging
import urllib
import urllib2
from google.appengine.api import urlfetch, memcache
from google.appengine.ext import ndb
from flask import Flask, jsonify, request, Response
import code
from StringIO import StringIO
import sys
from contextlib import contextmanager
import requests as req
import os
import time
from bs4 import BeautifulSoup
os.devnull =  os.path.devnull
if os.environ.get('SERVER_SOFTWARE','').startswith('Dev'):
    from google.appengine.tools.dev_appserver import FakeFilex
    FakeFile.ALLOWED_MODES = frozenset(['a','r', 'w', 'rb', 'U', 'rU'])
import dill

TOKEN= '50177117:AAEL3w8LlTI8bjoBIkC057at0jnZti75lcY'
BASE_URL = 'https://api.telegram.org/bot' + TOKEN + '/'
document = """
python2bot or PyBot for short is a bot that simulates a python (2.7.4) interpreter. It gives you access to an almost full featured python interpreter. It is for individual and group use. Groups share one interpreter! You can turn input on and off. You can also give it gist links and send their contents to the interpreter.

Commands:
/start - gives you this message
/clear - resets the python interpreter
/mypy - tells you if you are in python mode or not
/py - toggles python mode - if python mode is enable (TRUE) then each message that you send will be treated as python code being sent to an interpreter. In this mode, you can send multi-line commands as one message with \\ns and \\t as needed or you can send each line of a multi-line command as a seperate message. Either way, you need to terminate the multi-line command with /e 
/e - terminates a multi-line input. 
/python COMMAND - runs COMMAND throught the interpreter even if python mode is disable
/pylink GISTPAGE - finds the RAW of a gist page and sends it to the interpreter

Multi-line commands:
Multi-line commands are a bit tricky. First, telegram has no TAB functionality. Moreover, telegram does not even support "special" characters like \\t or \\n so support for them had to be added in the bot's code. Consquently, you must manually newline and tab your code using \\t and \\n. Second, in an interpreter, you have to hit RETURN to end a multi-line input. To emulate this in telegram, you send '/e' after you have finished sending the messagges that made up your multi-line command. Altenratively, /python assumes all commands are multi-line and requires no /e.

Pylink:
Pylink is rather experimental and could break easily if gist.github changes something. Simply supply it with the home page for some gist e.g. https://gist.github.com/teocollin1995/298b9f51df4fd963eeec and it will run all the python on that page

Disallowed libraries:
OS and Sys are disabled

Python Libraries used by this bot:
Dill, Code, Requests, Urllib, Logging, Json, bs4, StringIO, Flask, google, contextlib, sys, os

Contact:
github.com/teocollin1995

"""
#all times in seconds
MAX_EXEC_TIME = 15
KILL_TIME_ALLOWANCE = 5
LOCK_LIFE = MAX_EXEC_TIME + KILL_TIME_ALLOWANCE
CACHE_REFRESH_WAIT = .5

class Lock(object):
    """
    This is a memcached based lock. It works because memcache operations are atomic. 
    """
    def __init__(self, key):
        self.key = key
    def acquire(self, time_limit = False):
        if time_limit:
            expriration_time = time.time() + LOCK_LIFE #For if I wanted to limit the lock life for some reason
        
            while not memcache.add(self.key,"TRUE", time = expriration_time): 
                #try to add the key every CACHE_REFRESH_WAIT seconds
                #if the key is added, then another operation cannot add the key without returning false.
                time.sleep(CACHE_REFRESH_WAIT)
        else:
            while not memcache.add(self.key,"TRUE"):
                time.sleep(CACHE_REFRESH_WAIT)


    def release(self):
        memcache.delete(self.key)


class TimeoutError(Exception):
    """
    It is very easy to insert some code into the console that takes a long time to run. I use the limit_time function to run the code under a time limit. This exception is to be raised only if the time limit, MAX_EXEC_TIME, for limit_time to execute some code is execded.
    """
    "In case execution of user commands excedes MAX_EXEC_TIME"


def limit_time(timeout, code, *args, **kwargs):
    
    def tracer(frame, event, arg, start=time.time()):
        """
        We use a tracer to keep track of how long code has been running for. 
        It raises the timeout error in the event of this time exceding MAX_EXEC TIME  """
        now = time.time()
        if now > start + MAX_EXEC_TIME:
            raise TimeoutError(start, now)
        
        return tracer if event == "call" else None
    
    old_tracer = sys.gettrace()
    try:
        sys.settrace(tracer)
        code(*args, **kwargs)
    finally:
        sys.settrace(old_tracer)
  
#to run code and collect the output, we need to redirect it. These functions do that.  
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
            old_target, sys.stderr = sys.stderr, new_target # replace sys.stderr
            try:
                yield new_target # run some code with the replaced stderr
            finally:
                sys.stderr = old_target # restore to the previous value


class Member(ndb.Model): 
#represents one person with a name and a pymode bool telling the program if it should interpret their mesages as python code
    name = ndb.StringProperty()
    pymode = ndb.BooleanProperty()

class ChatInfo(ndb.Model):
    chat_id = ndb.StringProperty() 
    #This will be our key for the locks because there will be one console per CHAT not one console per user
    group_chat = ndb.BooleanProperty()
    console = ndb.PickleProperty()
    members = ndb.StructuredProperty(Member, repeated=True) #list of members each with their own pymode


app = Flask(__name__)




@app.route('/me')
def display_me():
    """ Just for testing purposes"""
    urlfetch.set_default_fetch_deadline(60)
    return json.dumps(json.load(urllib2.urlopen(BASE_URL + 'getMe')))

@app.route('/setwh')
def set_webhook():
    """Exists to setup the webhook from the telegram api to the appengine site"""
    urlfetch.set_default_fetch_deadline(60)
    return json.dumps(json.load(urllib2.urlopen(BASE_URL + 'setWebhook', urllib.urlencode({'url': "https://pybot-1023.appspot.com/webhook"}))))



@app.route('/webhook', methods=["PUT", "POST"])
def wh():
    """
    This is the function that is called when a message is sent to pybot.
    I choose to define most of the functions that rely on content from the message within this function.
    This results in an unacceptably long function, but I'd like to avoid thinking of this as a function and instead think of this
    as the main text of hte program. This also allows me to think of each interaction as one indepent run of this program where most functions are really procedures being based only on the contents of wh(). Tis a compromise.
    """

    urlfetch.set_default_fetch_deadline(60)
    r = request.get_json()
    logging.info("raw request:")
    logging.info(r)
    body = r
    
    #get items:
    #things present in all messages that we want to process:
    
    message = body['message']
    from_section = message.get('from')

    #apparently, you don't have to have all three of these...
    try:
        user_name = from_section["username"]
    except:
        user_name = ""
    
    try:
        last_name = from_section["last_name"]
    except:
        last_name = ""

    try:
        first_name = from_section["first_name"]
    except:
        first_name = ""
    
    fr =  user_name + last_name + first_name
    chat = message['chat']
    chat_id = str(chat['id'])
    lock_key = chat_id + "lock" #we don't want block any other uses that we might have for the chatid
    lock = Lock(lock_key) #lock down the communication for this chat
    message_id = message.get('message_id')
    date = message.get('date')
    
    #at this point we can define our reply function
    #from here until we begin to process the things that might vary from message to message in each chat
    #we will begin to define functions that depend on the chat related constant that every chat is garunteed to have
    #but take things that might vary from message to mesage as argument
    
    def give_response(chat_id, msg):
        try:
            resp = urllib2.urlopen(BASE_URL + 'sendMessage', urllib.urlencode({
                'chat_id': str(chat_id),
                'text': msg,
                'disable_web_page_preview': 'true',
                'reply_to_message_id': str(message_id),
            })).read()
        except:
            logging.warning("http error")
    #from here on all these functions operate automically on the database
    
    def create_new_user():
        """
        Check if a chat exists. If it a group chat, it will or something is wrong. If it is a group chat, make sure the user sending commands exists. 
        If it is not a group chat, create the chat and the user.
        """
        lock.acquire()
        query = ChatInfo.get_by_id(chat_id)
        if query is not None:
            #at least the chat already exists
            #is it a group chat or a single user chat
            if query.group_chat:
                #we now need to make sure this user in the group chat exists
                #This might not be concurrent - we might need a better way to do this.
                user_exists = any(map(lambda x: x.name == fr, query.members))
                if not user_exists:
                    
                    temp = Member()
                    temp.name = fr
                    temp.pymode = False
                    query.members.append(temp)
                    query.put()
                    
                                        
        else:
            #There is no user chat and we need to create it
            group_chat = ChatInfo(id = chat_id)
            group_chat.group_chat = False
            group_chat.chat_id = chat_id
            temp = code.InteractiveConsole()
            temp2 = dill.dumps(temp)
            group_chat.console = temp2
            group_chat.members = [Member(name=fr,pymode=False)]
            group_chat.key.id()
            group_chat.put()
        lock.release()
        
    


    def in_pymode():
        """
        Check if the current user is in py mode
        """
        lock.acquire()
        chat = ChatInfo.get_by_id(chat_id)
        for index,b in enumerate(chat.members):
            if b.name == fr:
                lock.release()
                return b.pymode
        lock.release()




    def toggle_pymode():
        """
        Toggle the current user's pymode status
        """
        lock.acquire()
        chat = ChatInfo.get_by_id(chat_id)
        
        for index,b in enumerate(chat.members):
            if b.name == fr:
                old = chat.members[index].pymode 
                chat.members[index].pymode = not old
                chat.put()
                lock.release()
                value = chat.members[index].pymode
                logging.info("toggling pymode of {} from {} to {}".format(fr,old, value))
                return value
        lock.release()



    #now we define the command processing function

    def process_command(cmd, runsource=False):
        """
        :param cmd - string that constitutes the cmd we want to run
        :param runsource - bool - True if want to treat the cmd as the print out of an individaul python file
        This function runs the given command and sends the output back to the chat. Runsource exists so that 
        the chat can link to python files and have pybot run them.
        """
        logging.info("starting to process command")
        f = StringIO() #fake files to redirect stdio/stderr into
        g = StringIO()
        executed = None #use to determine if more commands are required to finish this one
        lock.acquire(time_limit = True) #this could be dangerous
        chat = ChatInfo.get_by_id(chat_id) 
        console = dill.loads(chat.console) #unpickle our console - how does this scale???
        
        
        with redirect_stdout(f):
            with redirect_stderr(g):
                if not runsource:
                    executed = console.push(cmd) #run commands with our console 
                    #!!! COVER EXIT - this one exception carries through and is blocked by blocking the import of os and sys
                    chat.console = dill.dumps(console) #put the console back
                    chat.put()
                    lock.release()
                else:
                    executed = console.runcode(cmd) #if we bypass and send a whole file
                    chat.console = dill.dumps(console) #put the console back
                    chat.put()
                    lock.release()

                logging.info("Executed command with result: {}".format(str(executed)))
                
                
        if executed == False or runsource == True:
            cmd_res = "\"" + f.getvalue() + g.getvalue() + "\"" #later test if both are needed.
            logging.info("cmd result:")
            logging.info(cmd_res)
            give_response(chat_id, cmd_res);
        else:
            logging.info("Waiting for further input")
            give_response(chat_id, "Processed command:\n{}".format(cmd))
            
        
        



    
    def clear_console():
        """
        Reset the current chat's console
        """
        lock.acquire()
        chat = ChatInfo.get_by_id(chat_id)
        temp = code.InteractiveConsole() #create a new console
        chat.console = dill.dumps(temp) # replace it
        chat.put()
        lock.release()


        
    #Now we process things that might vary from message to message and react accordingly
   
    atext = None  
    
    atext = message.get('text') #If this message has an actual text message, atext will take on its value
    # otherwise, atex stays NONE indicating that the message does not have code we want to process
    #although it might have an operation on a group that we want to check for.
    if atext == None:
        # it is a group message or something we don't like e.g. a photo
        atext = message.get(u'new_chat_participant')  # is this a group is adding a new user so we add them to the chat?
        #These don't need to be transactional as there are single specific message types for group creation and destruction
       
        if atext != None: #the message is a group adding a user 
            group_chat = ChatInfo(id = chat_id)
            group_chat.group_chat = True
            group_chat.chat_id = chat_id
            temp = code.InteractiveConsole()
            temp2 = dill.dumps(temp)
            group_chat.console = temp2
            group_chat.members = [Member(name=fr,pymode=False)]
            group_chat.key.id()
            group_chat.put()
            give_response(chat_id, document)
            resp = Response(r, status=200)
            return resp
        else: # the message is not a group adding a user
            atext = message.get('left_chat_participant') #  are they removing a user?
            if atext != None: #let's remove the whole thing for now to clean the console
                del_group_chat = ChatInfo.get_by_id(chat_id)
                try:
                    del_group_chat.key.delete()
                except AttributeError:
                    logging.warn("Tried to delete non-existent group")
                resp = Response(r, status=200)
                return resp
            else: # nope, they are sending a photo or something...
                logging.info("Included non-text content")
                if in_pymode(): #if they sent it while in python interpertaion mode, we respond.
                    give_response(chat_id, "Action not allowed, ass")
                resp = Response(r, status=200)
                return resp

    else:
        #this is a user message.
        #we need to find if there is a new user and create them if needed
        #since an individual user request can start in many ways, this needs to be atomic
        create_new_user()
        #if we get past this point, we can be sure that a chat exists and the user exists and they had a message
        # now let's process the user's command
        # and yes, this is meant to carry on if this else statement is reached
        # the others terminate because they don't have code to respond to
    
    
    #deal with special chars in the mssage.
    btext = atext.rstrip("\\n")
    ctext = string.replace(btext, "\\t", '\t')
    text = string.replace(ctext, "\\n", '\n')
    #this is sloppy, fix it - generalize it - add more
    logging.info("text:")
    logging.info(text) #log the processed code

    #flag to be set if we want to process text even if pymode is not enabled by the user
    override_pymode = False
    
    #commands that transform the text/command are to be processed first
    if text[0] == '/':
        if text[0:7] == '/python': #send the code to the interpreter without invoking python mode
            text = text[8:]
            override_pymode = True
        if text[0:4] == '/b ': #experimental - not to be included in docs yet
            override_pymode = True
        elif text[0:7] == '/pylink': # try to set the text to code in a linked gist
            link = text[8:]
            if 'gist.github' not in link: #use regex later - simple test but might be easy to fool
                logging.warn("someone attempted to send invalid link")
                give_response(chat_id, "Invalid link")
                resp = Response(r, status=200)
                return resp
            
            paste = req.get(link) # get the code
            if not paste: # test if not status 200
                logging.warn("Possible server to pasterpin connection issue")
                give_response(chat_id, "Invalid link or connection issue")
                resp = Response(r, status=200)
                return resp
            logging.info(paste.text)
            soup = BeautifulSoup(paste.text)
            links = soup.find_all('a') 
            logging.info("soup:\n:{}".format(soup.prettify().encode('utf-8')))
            try:
                newlink = 'https://gist.githubusercontent.com' + [x for x in links if 'Raw' in x.text][0].get('href') 
                #finds the Raw page where the code is easy to get
                logging.info("Newlink is: {}".format(newlink))
            except IndexError: #in case something goes wrong and no raw page is there
                logging.warn("Error fiding raw")
                give_response(chat_id, "Invalid link")
                resp = Response(r, status=200)
                return resp
            paste2 = req.get(newlink)
            if not paste2:
                logging.warn("someone attempted to send invalid link or a link not to raw")
                give_response(chat_id, "Invalid link")
                resp = Response(r, status=200)
                return resp
            text = paste2.text.replace('\r','\n') 
            override_pymode = True #set the text to the code in the gist and set it to be interpreted
            logging.info("py link text\n:{}".format(text.encode('utf-8')))


    #as that was the last point to change the test, how about if it actually says anything?
    if text == "" or text == None:
        give_response(chat_id, "Messages require actual content")
        resp = Response(r, status=200)
        return resp
    
        
            
    #Process text to check for minor commands that don't transform the text
    
    if text[0] == '/': #it is a command
        if text == '/py': #toggle py mode
            ret = toggle_pymode()
            give_response(chat_id, "toggled python mode to {}".format(str(ret)))
        elif text == '/start' or text == '/help' or text == '/commands':
            give_response(chat_id,document)
            resp = Response(r, status=200) 
            return resp    
        elif text == '/clear':
            clear_console()
        elif text == '/e':
            process_command('\n')
        elif text == '/mypy':
            py = in_pymode()
            give_response(chat_id, "You are in pymode: {}".format(str(py)))
       
    else:

        #at this point, if they are not in pymode, we should be discarding all input
        if not in_pymode() and not override_pymode:
            logging.info("Discarded input because in pymode")
            resp = Response(r, status=200) 
            return resp  

        else:
            logging.info("Checking for illegal inputs")
            #Okay, they probably want us to process a command
            #let's make sure it isn't a dangerous one
            #please brainstorm more of these
            if 'import os' in text:
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
                logging.info("Entering transactional to process command")
                #Okay, let's do this
                try:
                    #process_command(text, runsource = override_pymode)
                    limit_time(MAX_EXEC_TIME, process_command, text, runsource = override_pymode)
                except TimeoutError:
                    logging.info("Command took too long and was killed")
                    give_response(chat_id, "Max execution time exceded")

        
    resp = Response(r, status=200) 
    return resp    
    # ^ say that something happened - it is important to have these so telegram doesn't keep send mssages that we processed 
        
    
    
    


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
