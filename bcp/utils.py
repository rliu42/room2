import imp
import threading
import requests, json

import logging
from datetime import datetime
logging.basicConfig(filename='room2.log', level=logging.DEBUG)

def setInterval(interval, name):
    def decorator(function):
        def wrapper(*args, **kwargs):
            stopped = threading.Event()
            def loop():
                while not stopped.is_set(): 
                    stopped.wait(interval)
                    #logging.info("[%s] calling function %s" % (name, datetime.now().strftime('%H:%M:%S')))
                    function(*args, **kwargs)
                #logging.debug("[%s] SET INTERVAL STOPPED" % (name))
            t = threading.Thread(target=loop)
            t.daemon = True # stop if the program exits
            t.start()
            return stopped
        return wrapper
    return decorator

try:
    # Windows
    from msvcrt import getch
    getKey = getch
except ImportError:
    # Unix / Mac OS
    import termios, tty, sys, os
    def getKey():
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        new = termios.tcgetattr(fd)
        new[3] = new[3] & ~termios.ICANON & ~termios.ECHO
        new[6][termios.VMIN] = 1
        new[6][termios.VTIME] = 0
        termios.tcsetattr(fd, termios.TCSANOW, new)
        key = None
        try:
            key = os.read(fd, 3)
        finally:
            termios.tcsetattr(fd, termios.TCSAFLUSH, old)
        return key

try:
    imp.find_module('RPi')
    import RPi.GPIO as GPIO
except ImportError:
    print "-------------------------"
    print "RPi Not Found. DEBUG MODE"
    print "-------------------------"
    SERVER_URL = "http://localhost:8000"
    print "Posting to node server at %s" % (SERVER_URL)
    print "--------------------------------------------"
    debug = True
