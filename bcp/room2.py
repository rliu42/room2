from flask import Flask
import os, subprocess, time, math, logger
from collections import defaultdict
from constants import *
from utils import *

from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler

import logging
logging.basicConfig(filename='room2.log', level=logging.DEBUG)

CONTROLLER_ID = "room2";
listeners = False

app = Flask(__name__)

if not debug:
    GPIO.setmode(GPIO.BOARD)

isBlinking = defaultdict(bool)
pinValues = defaultdict(int)
pinObject = {}
pinTimers = {}

@app.route('/')
def getPins():
    return json.dumps(pinValues)

# Outputs

@app.route('/<io>/<pin>/<value>')
def setpin(io, pin, value):
    pin, value = int(pin), int(value)
    try:
        if io == 'output':
            if not debug: 
                value = GPIO.HIGH if (value == 1) else GPIO.LOW
        if pin in pinTimers:
            logging.debug("Clearing blink timer on channel %s" % (pin))
            pinTimers[pin].set()
            del pinTimers[pin]
    except Exception as e:
        logging.error("Error clearing blink timer %s" % (e))
    finally:
        try:
            isBlinking[pin] = False
            if not debug:
                if not pin in pinValues:
                  initpin(pin, io, value)
                if io == 'pwm':
                    if value == 0:
                        pinObject[pin].stop()
                    else:
                        pinObject[pin].start(value)
                elif io == 'output':
                    pinObject[pin] = GPIO.output(pin, value)
            pinValues[pin] = value
        except Exception as e:
            logging.error("Error setting pin %s" % (e))
        finally:
            return 'Pin Number: %s <br />Duty: %s %s' % (pin, value, getPins())


@app.route('/initpin/<pin>/<io>/<value>')
def initpin(pin, io, value):
    # initialize an input/output pin
    logging.debug("Initializing pin at /initpin/%s/%s/%s" % (pin, io, value))
    pin, value = int(pin), int(value)
    try:
        if io == 'output':
            if not debug: 
                value = GPIO.HIGH if (value == 1) else GPIO.LOW
        pinValues[pin] = value if io == 'pwm' or io == 'output' else 'input'
        if not debug:
            if io == 'output':
                if not pin in pinObject:
                    GPIO.setup(pin, GPIO.OUT)
                    pinObject[pin] = GPIO.output(pin, GPIO.HIGH)
            elif io == 'pwm':
                if not pin in pinObject:
                    GPIO.setup(pin, GPIO.OUT)
                    pinObject[pin] = GPIO.PWM(pin, FREQUENCY)
                pinObject[pin].start(value)
            elif io == 'input':
                if not pin in pinObject:
                    GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_DOWN)
    except Exception as e:
        logging.error("Error initializing pin %s" % (e))
    finally:
        return 'Pin %s set to %s %s' % (pin, io, getPins())

@app.route('/blink/<pin>/<io>/<interval>/<high>')
def blink(pin, io, high, interval=750):
    logging.debug("Blinking pin /blink/%s/%s/%s/%s" % (pin, io, interval, high))
    pin, interval, high = int(pin), int(interval), int(high)
    if pin in pinTimers:
        pinTimers[pin].set()
        del pinTimers[pin]
    if not debug:
        try:
            if not pin in pinValues:
                initpin(pin, io, 0)
            @setInterval(1.0*interval/1000, "blink")
            def blinker(pin):
                if pinValues[pin] == 0:
                    pinValues[pin] = high
                    if io == "pwm":
                        pinObject[pin].start(high)
                    if io == "output":
                        GPIO.output(pin, GPIO.LOW)
                else:
                    pinValues[pin] = 0
                    if io == "pwm":
                        pinObject[pin].stop()
                    if io == "output":
                        GPIO.output(pin, GPIO.HIGH)
            pinTimers[pin] = blinker(pin)
            isBlinking[pin] = True
        except Exception as e:
            logging.error("Could not spawn blinking thread on channel %s" % (pin))
            # Set to purple if pedestal blinking failed
            if pin in redLED.values():
                element = (key for key, value in redLED.items() if value == pin).next()
                setpin("output", redLED[element], 1)
                setpin("output", blueLED[element], 1)
                logging.debug("Setting %s light to PURPLE instead" % (element))
                isBlinking[pin] = True
        finally:
            return "Blinking channel %s" % (pin)
    else:
        return blink_debug(pin, high, interval)

@app.route('/stop/<pin>')
def stop(pin):
    logging.debug("Stopping pin %s" % (pin))
    pin = int(pin)
    try:
        if pin in pinTimers:
            pinTimers[pin].set()
            del pinTimers[pin]
        if pin in pinObject:
            pinObject[pin].stop()
        if pin in pinValues:
            pinValues[pin] = 0
    except Exception as e:
        logging.error("Error stopping pin %s" % (pin))
    finally:
        return "Stopped channel %s" % (pin)

def blink_debug(pin, high, interval=750):
    if not pin in pinValues:
        pinValues[pin] = 0
    @setInterval(1.0*interval/1000, "Blink debug")
    def blinker(pin):
        if pinValues[pin] == 0:
            pinValues[pin] = high
        else:
            pinValues[pin] = 0
        print 'Pin %s blinking: %s' % (pin, pinValues[pin])
        logging.debug('Pin %s blinking: %s' % (pin, pinValues[pin]))
    pinTimers[pin] = blinker(pin)
    isBlinking[pin] = True
    return "Blinking channel %s" % (pin)

inputChannels = [7]
channelSelection = {}

@app.route('/initlisteners')
def initlisteners():
    global firstContact
    if not debug:
        for channel in inputChannels:
            channelSelection[channel] = False
            try: 
                GPIO.add_event_detect(channel, GPIO.BOTH, callback=toggle, bouncetime=300)
                logging.debug("channel %s listener initialized" % (channel))
            except Exception as e:
                listeners = True
                pass
    resetPedestal(stop=True)
    return "Listeners initialized"

def toggle(channel):
    url = "%s/input/%s/%s/1" % (SERVER_URL, CONTROLLER_ID, channel)
    time.sleep(0.1)
    logging.debug("Input for channel %s is %s\n" % (channel, GPIO.input(channel)))
    if channelSelection[channel]:
        # deselection
        # check that the state wasn't just noise
        if GPIO.input(channel):
            time.sleep(0.1)
            if GPIO.input(channel):
                channelSelection[channel] = False
                url = "%s/input/%s/%s/1" % (SERVER_URL, CONTROLLER_ID, channel)
                logging.debug("ON %s\nPosting to %s"  % (channel, url))
    else:
        # selection
        # check that state wasn't just noise
        if not GPIO.input(channel):
            time.sleep(0.1)
            if not GPIO.input(channel):
                time.sleep(0.1)
                if not GPIO.input(channel):
                    time.sleep(0.1)
                    if not GPIO.input(channel):
                        time.sleep(0.1)
                        if not GPIO.input(channel):
                            channelSelection[channel] = True
                            url = "%s/input/%s/%s/0" % (SERVER_URL, CONTROLLER_ID, channel)
                            logging.debug("OFF %s\nPosting to %s"  % (channel, url))
    try:
        requests.get(url, timeout=1)
    except Exception as e:
        logging.debug("ERROR posting to %s\n" % (url))

chargeCount = {"AIR": 0, "WATER": 0, "FIRE": 0, "EARTH": 0, "DARKNESS": 0}
charged = {"AIR": False, "WATER": False, "FIRE": False, "EARTH": False, "DARKNESS": False}
next_element = None
firstContact = False

def getNextElement():
    for element in elementOrder:
        if not charged[element]:
            return element
    return "DONE"

def getChargeColor(charge):
    blue = math.ceil(100 * charge / CHARGE_THRESHOLD)
    red = 100 - blue
    return (red, blue)


def postCharge(element):
    url = "%s/input/%s/%s/1" % (SERVER_URL, CONTROLLER_ID, elementInputMap[element])
    logging.debug("Posting to %s" % (url))
    try:
        r = requests.get(url, timeout=1)
        logging.debug("Posted successfully to %s" % (url))
    except:
        logging.debug('Error posting to %s' % (url))
    print_update()
    return

def listenPedestal(timers):
    global listeners, firstContact
    if not listeners:
        print('Pesdestal listeners initialized. Press "X" to terminate')
        print_update()
        listeners = True
        lastTime = time.time()
        lastCharge = time.time()
        while True:
             key = str(getKey()).strip().upper()
             print(key + ' pressed')
             if key == "X":
                break
             now = time.time()
             if now - lastTime > 5:
                print_update()
             lastTime = now
             try:
                key = key[0]
             except:
                key = ""
             if key in elementKeyMap:
                element = elementKeyMap[key]
                if element == next_element and isPedestalOn():
                    # user is charging the correct element
                    if not firstContact:
                        firstContact = True
                    chargeCount[element] += 1
                    charge = chargeCount[element]
                    print("Charging %s: %s/%s" % (element, charge, CHARGE_THRESHOLD))
                    if charge == NOISE_THRESHOLD and now - lastCharge > 5:
                        u = SERVER_URL + "/begin_charge"
                        try:
                            r = requests.get(u)
                            lastCharge = now
                        except Exception as e:
                            print(str(e))
                    if charge >= CHARGE_THRESHOLD:
                        print("Finished charging " + element.upper())
                        setpin("output", redLED[element], 0)
                        charged[element] = True
                        postCharge(element)
                    elif charge > NOISE_THRESHOLD:
                        # adjust pedestal LED gradually from red to blue
                        try: 
                            if redLED[element] in timers:
                                timers[redLED[element]].set()
                                del timers[redLED[element]]
                            setpin("output", redLED[element], 1)
                            setpin("output", blueLED[element], 1)
                        except Exception as e:
                            print(str(e))
                            pass
                else:
                    # user is charging the incorrect element
                    if isPedestalOn():
                        print (element + " contact. Should be charging " + next_element)
                    else:
                        print (element + " contact. Pedestal has NOT been unlocked.")
        print("Pedestal listeners terminated")


def print_update():
    global next_element
    global charged
    url = SERVER_URL + "/pedestal_state"
    try:
        r = requests.get(url, timeout=1)
        charged = json.loads(r.text)
    except:
        pass
    next_element = getNextElement()
    print("Key mapping: " + str(elementKeyMap))
    print("Charge state: " + str(charged))
    print("Next element to charge: " + next_element)

@setInterval(DECHARGE_RATE, "Decharger")
def decharger(blinkingState):
    if firstContact:
        for element in chargeCount:
            if not charged[element] and pinValues[blueLED[element]] != 1:
                chargeCount[element] = max(0, chargeCount[element]-1)
                charge = chargeCount[element]
                if element == next_element and charge > 0:
                    print("Decharging %s: %s/%s" % (element, charge, CHARGE_THRESHOLD))
                if charge > NOISE_THRESHOLD and charge < CHARGE_THRESHOLD:
                        setpin("output", redLED[element], 1)
                        setpin("output", blueLED[element], 1)
                elif charge == 0:
                    if element == next_element:
                        if not isBlinking[redLED[element]] and isPedestalOn():
                            blink(redLED[element], "output", 1, 400)
                        if pinValues[blueLED[element]] != 0:
                            setpin("output", blueLED[element], 0)

def isPedestalOn():
    return (pinValues[redLED["DARKNESS"]] + pinValues[blueLED["DARKNESS"]]) > 0

def resetPedestal(stop=False):
    global firstContact
    for element in elementOrder:
        if stop:
            setpin("output", redLED[element], 0)
            setpin("output", blueLED[element], 0)
        chargeCount[element] = 0
    firstContact = False
    out = open("room2.log", "w")
    out.write("")
    out.close()

class pedestalThread(threading.Thread):

    def __init__(self, pinTimers, blinkingState):
        super(pedestalThread, self).__init__()
        self.pinTimers = pinTimers
        self.blinkingState = blinkingState

    def run(self):
        print "Starting Pedestal listeners..."
        timer = decharger(self.blinkingState)
        listenPedestal(self.pinTimers)
        print "Killing Pedestal listener..."
        timer.set()
        print "Resetting Pedestal"
        resetPedestal(stop=True)


if __name__ == '__main__':
    thread = pedestalThread(pinTimers, isBlinking)
    thread.start();
    server = pywsgi.WSGIServer(('', 4000), app, handler_class=WebSocketHandler)
    server.serve_forever()
    #app.run(debug=True, host='0.0.0.0', port=4000)