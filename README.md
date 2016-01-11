PyBot
====================
 
python2bot or PyBot for short is a telegram bot that simulates a python (2.7.4) interpreter. It gives you access to an almost full featured python interpreter. It is for individual and group use. Groups share one interpreter! You can turn input on and off. You can also give it gist links and send their contents to the interpreter.

Commands:
---------------------
* /start - gives you this message
* /clear - resets the python interpreter
* /mypy - tells you if you are in python mode or not
* /py - toggles python mode - if python mode is enable (TRUE) then each message that you send will be treated as python code being sent to an interpreter. In this mode, you can send multi-line commands as one message with \\ns and \\t as needed or you can send each line of a multi-line command as a seperate message. Either way, you need to terminate the multi-line command with /e 
* /e - terminates a multi-line input. 
* /python COMMAND - runs COMMAND throught the interpreter even if python mode is disable
* /pylink GISTPAGE - finds the RAW of a gist page and sends it to the interpreter

Multi-line commands:
---------------------
Multi-line commands are a bit tricky. First, telegram has no TAB functionality. Moreover, telegram does not even support "special" characters like \\t or \\n so support for them had to be added in the bot's code. Consquently, you must manually newline and tab your code using \\t and \\n. Second, in an interpreter, you have to hit RETURN to end a multi-line input. To emulate this in telegram, you send '/e' after you have finished sending the messagges that made up your multi-line command. Altenratively, /python assumes all commands are multi-line and requires no /e.

Pylink:
---------------------
Pylink is rather experimental and could break easily if gist.github changes something. Simply supply it with the home page for some gist e.g. https://gist.github.com/teocollin1995/298b9f51df4fd963eeec and it will run all the python on that page

Disallowed libraries (from within the console):
---------------------
OS and Sys are disabled

Libraries used from by this bot:
---------------------
Dill, Code, Requests, Urllib, Logging, Json, bs4, StringIO, Flask, google, contextlib, sys, os

Note that I'm not including a depends.txt as for now this github is just for show.

Issues
---------------------
There are really three major issues.

### Testing
I haven't tested this thoroughly. It was able to use it with my friends without having a serious issue for around 100 days but that doesn't say much at all. I need to come up with a better way of testing


### Time limits
Currently, the program won't allow any bit of code's execution time to last longer than 15 seconds. So when I say this is a fully featured interpret, I'm kind of lying because that is only true on a super fast server. The reason these time limits exist is that it is really easy to create code that runs for a long time and that clogs up the server. Worse, it means that all the messages that are sent to pybot are going keep bouncing around and will probably be processed out of order, rseulting in unspeakable horrors. The time limit of 15 seconds seems to be enough to avoid this.


### Dill/pickle
This code uses dill and pickle, heavily. Afterall, what is the other easy way to share an interpreter session between multiple servers? Now, the problem is that dill/pickle have obvious security problems and I very much agree that this kind of makes using them back practice. I also prefer text whenever possible. So in the future I need to find another way of sharing interpreter sessions.
