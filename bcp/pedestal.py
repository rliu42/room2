import math, sys, time
from constants import *
from utils import *

CONTROLLER_ID = "room2";
listeners = False

if not debug:
	GPIO.setmode(GPIO.BOARD)

pinValues = {}
pinObject = {}
pinTimers = {}

def setpin(io, pin, value):
	# set PIN to be VALUE (duty)
	pin = int(pin)
	value = float(value)
	if io == 'output':
		value = GPIO.HIGH if value == 1 else GPIO.LOW
	if pin in pinTimers:
		print ('Clearing blink timer')
		pinTimers[pin].set()
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

def initpin(pin, io, value):
	# initialize an input/output pin
	pin = int(pin)
	value = int(value)
	if io == 'output':
		if not debug: 
			value = GPIO.HIGH if (value == 1 or value == GPIO.HIGH) else GPIO.LOW
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
				GPIO.setup(pin, GPIO.IN, pull_up_down = GPIO.PUD_UP)

	return 'Pin %s set to %s %s' % (pin, io, "")


chargeCount = {"AIR": 0, "WATER": 0, "FIRE": 0, "EARTH": 0, "DARKNESS": 0}
charged = {"AIR": False, "WATER": False, "FIRE": False, "EARTH": False, "DARKNESS": False}
next_element = None

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
	url = SERVER_URL + "/input/" + str(CONTROLLER_ID) + "/" + str(elementInputMap[element]) + "/1"
	print("Posting to " + url)
	try:
		r = requests.get(url, timeout=1)
	except:
		if debug:
			charged[element] = True
		print('Error posting to ' + url)
	print_update()
	return

def listenPedestal():
	global listeners
	if not listeners:
		print('Pesdestal listeners initialized. Press "X" to terminate')
		print_update()
		listeners = True
		lastTime = time.time()
		while True:
			 key = str(getKey()).strip().upper()
			 print(key + ' pressed')
			 if key == "X":
			 	resetPedestal(True)
			 if time.time() - lastTime > 5:
			 	print_update()
			 lastTime = time.time()
			 key = key[0]
			 if key in elementKeyMap:
			 	element = elementKeyMap[key]
			 	if element == next_element:
			 		# user is charging the correct element
					chargeCount[element] += 1
					charge = chargeCount[element]
					print("Charging " + element + ": " + str(charge) + "/" + str(CHARGE_THRESHOLD))
					if charge > CHARGE_THRESHOLD:
						print("Finished charging " + element.upper())
						postCharge(element)
					elif charge > NOISE_THRESHOLD:
						# adjust pedestal LED gradually from red to blue
						try: 
							red, blue = getChargeColor(charge)
							if not debug:
								setpin("pwm", redLED[element], red)
								setpin("pwm", blueLED[element], blue)
							print "red: %s, blue: %s" %(red, blue)
						except:
							pass
				else:
					# user is charging the incorrect element
					print (element + " contact. Should be charging " + next_element)

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
	print("Charge order: " + str(elementOrder))
	print("Charge state: " + str(charged))
	print("Next element to charge: " + next_element)

@setInterval(DECHARGE_RATE)
def decharger():
	global chargeCount
	for element in chargeCount:
		if not charged[element]:
			chargeCount[element] = max(0, chargeCount[element]-1)
			charge = chargeCount[element]
			if element == next_element and charge > 0:
				print("Decharging " + element + ": " + str(charge) + "/" + str(CHARGE_THRESHOLD))
			if charge > NOISE_THRESHOLD:
				try: 
					red, blue = getChargeColor(charge)
					if not debug:
						setpin("pwm", redLED[element], red)
						setpin("pwm", blueLED[element], blue)
					print "red: %s, blue: %s" %(red, blue)
				except:
					pass
			elif charge > 0:
				setpin("pwm", redLED[element], 100)
				setpin("pwm", blueLED[element], 0)

def resetPedestal(stop=False):
	for element in elementOrder:
		if not debug:
			if stop:
				setpin("pwm", redLED[element], 0)
				setpin("pwm", blueLED[element], 0)
		chargeCount[element] = 0

if __name__ == '__main__':
	timer = decharger()
	listenPedestal()
	timer.set()
	try:
		resetPedestal(stop=True)
	except:
		pass
	sys.exit()