from flask import Flask
from constants import *
from utils import *

CONTROLLER_ID = "room1";
listeners = False

app = Flask(__name__)

if not debug:
    GPIO.setmode(GPIO.BOARD)
    GPIO.setup(5, GPIO.OUT)
    GPIO.setup(13, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    p = GPIO.PWM(5, FREQUENCY)
    p.start(50)

pinValues = {}
pinObject = {}
pinTimers = {}

@app.route('/')
def getPins():
    pinValues['server'] = SERVER_URL
    return json.dumps(pinValues)

@app.route('/setip/<host>')
def setServerIP(host):
    global SERVER_URL
    SERVER_URL = "http://" + host
    print "SERVER_URL set to %s" % (SERVER_URL)
    return SERVER_URL

# Outputs

@app.route('/<io>/<pin>/<value>')
def setpin(io, pin, value):
    # set PIN to be VALUE (duty)
    pin, value = int(pin), int(value)
    if io == 'output':
        if not debug:
            value = GPIO.HIGH if value == 1 else GPIO.LOW
    if pin in pinTimers:
        print ('Clearing blink timer on channel %s' % (pin))
        pinTimers[pin].set()
        del pinTimers[pin]
    if not debug:
        if not pin in pinValues:
          initpin(pin, io, value)
        if io == 'pwm' or io == 'clock':
            if value == 0:
                pinObject[pin].stop()
            else:
                if io == 'clock':
                    value = 1.0*value/10
                pinObject[pin].start(value)
        elif io == 'output':
            pinObject[pin] = GPIO.output(pin, value)

    pinValues[pin] = value

    return 'Pin Number: %s <br />Duty: %s %s' % (pin, value, getPins())


@app.route('/initpin/<pin>/<io>/<value>')
def initpin(pin, io, value):
    # initialize an input/output pin
    pin, value = int(pin), int(value)
    if io == 'output':
        if not debug: 
            value = GPIO.HIGH if (value == 1 or value == GPIO.HIGH) else GPIO.LOW
    pinValues[pin] = value if io == 'pwm' or io == 'output' or io == 'clock' else 'input'
    if not debug:
        if io == 'output':
            if not pin in pinObject:
                GPIO.setup(pin, GPIO.OUT)
                pinObject[pin] = GPIO.output(pin, GPIO.HIGH)
        elif io == 'pwm' or io == 'clock':
            if not pin in pinObject:
                GPIO.setup(pin, GPIO.OUT)
                pinObject[pin] = GPIO.PWM(pin, FREQUENCY)
            if io == 'clock':
                value = 1.0*value/10
            pinObject[pin].start(value)
        elif io == 'input':
            if not pin in pinObject:
                GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)

    return 'Pin %s set to %s %s' % (pin, io, getPins())

@app.route('/blink/<pin>/<io>/<interval>/<high>')
def blink(pin, io, high, interval=750):
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
        except Exception as e:
            pass
        finally:
            return "Blinking channel %s" % (pin)
    else:
        return blink_debug(pin, high, interval)

@app.route('/stop/<pin>')
def stop(pin):
    pin = int(pin)
    if pin in pinTimers:
        pinTimers[pin].set()
        del pinTimers[pin]
    if pin in pinObject:
        pinObject[pin].stop()
    if pin in pinValues:
        pinValues[pin] = 0
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
    pinTimers[pin] = blinker(pin)
    return "Blinking channel %s" % (pin)

bookSelection = {}

@app.route('/initlisteners')
def initlisteners():
    global listeners
    if not debug and not listeners:
        for channel in bookChannels:
            try: 
                GPIO.add_event_detect(channel, GPIO.BOTH, callback=toggle, bouncetime=300)
            except RuntimeError as e: 
                listeners = True
                print(str(e))
            bookSelection[channel] = False
    listeners = True
    return 'listeners initialized'

def toggle(channel):
    if (channel in bookSelection and bookSelection[channel]):
        # deselection
        bookSelection[channel] = False
        print ("Deselected " + str(channel))
        url = "%s/input/%s/%s/0" % (SERVER_URL, CONTROLLER_ID, channel)
        print ("Posting to " + url)
    else:
        # selection
        bookSelection[channel] = True
        print ("Selected " + str(channel))
        url = "%s/input/%s/%s/1" % (SERVER_URL, CONTROLLER_ID, channel)
        print ("Posting to " + url)
    try:
        requests.get(url, timeout=1)
    except:
        print('Error posting to ' + url)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
