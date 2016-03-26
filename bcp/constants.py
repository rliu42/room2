# Address of node.js server
SERVER_URL = '';

# PWM Frequency
FREQUENCY = 100

# Debug mode
debug = False

# Room 1 bookshelf inputs
bookChannels = [29, 31, 33, 35, 37]

# Room 2 pedestal I/O
elementInputMap = {"AIR": 29, "WATER": 31, "FIRE": 33, "EARTH": 35, "DARKNESS": 37}
blueLED = {"AIR": 23, "WATER": 16, "FIRE": 10, "EARTH": 26, "DARKNESS": 12}
redLED = {"AIR": 21, "WATER": 22, "FIRE": 18, "EARTH": 24, "DARKNESS": 8}

# Pedestal spec
elementOrder = ["AIR", "WATER", "FIRE", "EARTH", "DARKNESS"]
elementKeyMap = {"G": "AIR", "D": "WATER", "A": "FIRE", "S": "EARTH", "F": "DARKNESS"}

# Pedestal charging
CHARGE_UNIT = 6
DECHARGE_RATE = 1 # seconds per unit
NOISE_THRESHOLD = 2
CHARGE_THRESHOLD = CHARGE_UNIT * 8 + NOISE_THRESHOLD
