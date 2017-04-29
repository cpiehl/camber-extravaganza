##############################################################
# Camber Extravaganza!
# App for showing camber in real time
# Useful for tuning?
# https://github.com/cpiehl/camber-extravaganza
#
# TODO:
#   - multi-language support
#
# Changelog:
#
# V1.0  - Initial version
#       - instant and peak values with flappers
#
# V1.1  - Graphs
#       - color spectrum instead of color steps
#       - self-normalizing graphs
#       - log scale graphs
#       - options menu
#
# V1.11 - Save/Load options
#       - Text inputs for size, radscale, peaktime, etc
#
# V1.12 - Configurable target camber
#
# V1.13 - Show average camber toggle option
#       - Switch to HSV colors for spectrum
#
# V1.14 - Optimal camber calculated from config files
#
# V1.15 - Draw tires, suspension, chassis, target camber
#       - UI cleanup, remove some unnecessary options
#       - Savedata sanitizing
#
# V1.16 - FPS fix - Only render when app is activated
#       - tyres-data.json - Full list of all base and DLC cars' tyre data
#       - tyres-data-custom.json - Optionally load this file for mod cars
#
# V1.17 - Dynamically factor in weight balance and inside wheel camber grip
#
#############################################################

import ac
import acsys
import collections
import colorsys
import json
import math
import os
import pickle

appWindow = 0
CamberIndicators = {}
CheckBoxes = {}
Buttons = {}
TextInputs = {}
Labels = {}
redrawText = False
Options = {
	"drawGraphs": False,
	"normalize": False,
	"useSpectrum": True,
	"alpha": 0.5,        # graph alpha
	"tireHeight": 50,    # tire height
	"radScale": 10,      # scale flapper deflection to this at 2*peak grip
	"graphWidth": 150,   # in pixels, also the number of frames of data to display
	"graphHeight": 85,   # in pixels
	"targetCamber": 999, # degrees
	"optimalCamberF": 999, # degrees
	"optimalCamberR": 999, # degrees
	"dcamber0": 999,     # initial
	"dcamber1": -999,    # initial
	"tyreCompound": "",  # short name
	"tireRadius": 1      # default, in meters
}
SavableOptions = [ # Only save these to file
	"drawGraphs",
	"normalize",
	"useSpectrum"
]
doRender = True


class CamberIndicator:
	def __init__(self, app, x, y):
		global Options
		self.xPosition = x
		self.yPosition = y
		self.value = 0
		self.avgValue = 0
		self.color = {'r':1,'g':1,'b':1,'a':1}
		self.serie = collections.deque(maxlen=Options["graphWidth"])
		self.minVal = Options["targetCamber"] * 1.5
		self.maxVal = 1.5

		self.valueLabel = ac.addLabel(appWindow, "0.0°")
		ac.setPosition(self.valueLabel, x, y)
		self.avgValueLabel = ac.addLabel(appWindow, "0.0°")
		ac.setPosition(self.avgValueLabel, x, y + 18)


	def setValue(self, value, deltaT, optimal):
		global Options
		self.value = value
		deg = math.degrees(self.value)
		#~ otherdeg = math.degrees(othervalue)
		#~ diff = deg - otherdeg
		ac.setText(self.valueLabel,"{0:.3f}°".format(deg))
		#~ text = getGripFactor(Options["dcamber0"], Options["dcamber1"], value)
		#~ ac.setText(self.valueLabel,"{0:.1f}%".format(text)

		self.color = getColor(deg, optimal)
		self.serie.append({"value":deg,"color":self.color})

		serieSum = 0
		for s in self.serie:
			serieSum += s["value"]
		self.avgValue = serieSum / len(self.serie)
		ac.setFontColor(self.avgValueLabel,
			self.color['r'],
			self.color['g'],
			self.color['b'],
			self.color['a']
		)
		ac.setText(self.avgValueLabel,"{0:.3f}°".format(self.avgValue))


	def drawTire(self, suspX, suspY, suspH, flip=False):
		global Options

		x = self.xPosition + 25
		y = self.yPosition
		#~ rad = self.value * Options["radScale"]
		rad = self.value * Options["radScale"] / (2 * -Options["targetCamber"])
		if flip:
			#~ x = self.xPosition + 50
			rad = math.pi - rad

		ac.glColor4f(
			self.color['r'],
			self.color['g'],
			self.color['b'],
			self.color['a']
		)

		h = Options["tireHeight"]
		w = h / 2
		cosrad = math.cos(rad)
		sinrad = math.sin(rad)
		halfpi = math.pi/2
		if flip:
			cosradnorm = math.cos(rad+halfpi)
			sinradnorm = math.sin(rad+halfpi)
			# Have to draw counterclockwise
			ac.glBegin(acsys.GL.Quads)
			ac.glVertex2f(x, y)
			ac.glVertex2f(x+h*cosradnorm, y+h*sinradnorm)
			ac.glVertex2f(x+w*cosrad+h*cosradnorm, y+w*sinrad+h*sinradnorm)
			ac.glVertex2f(x+w*cosrad, y+w*sinrad)
			ac.glEnd()
		else:
			cosradnorm = math.cos(rad-halfpi)
			sinradnorm = math.sin(rad-halfpi)
			# Have to draw counterclockwise
			ac.glBegin(acsys.GL.Quads)
			ac.glVertex2f(x, y)
			ac.glVertex2f(x+w*cosrad, y+w*sinrad)
			ac.glVertex2f(x+w*cosrad+h*cosradnorm, y+w*sinrad+h*sinradnorm)
			ac.glVertex2f(x+h*cosradnorm, y+h*sinradnorm)
			ac.glEnd()

		# Suspension bits
		ac.glColor4f(0.9, 0.9, 0.9, 0.9)
		ac.glBegin(acsys.GL.Lines)
		ac.glVertex2f(x+(h/2 - suspH)*cosradnorm, y+(h/2 - suspH)*sinradnorm)
		ac.glVertex2f(suspX, suspY + suspH)
		ac.glVertex2f(x+(h/2 + suspH)*cosradnorm, y+(h/2 + suspH)*sinradnorm)
		ac.glVertex2f(suspX, suspY - suspH)
		ac.glEnd()


	def drawGraph(self, flip=False):
		global Options
		x = self.xPosition
		y = self.yPosition - 10
		dx1 = 55
		dx2 = dx1 + Options["graphWidth"]
		f = 1 # flip mult thisisreallydumbbutineedit
		if flip:
			dx1 = -5
			dx2 = dx1 - Options["graphWidth"]
			f = -1

		halfHeight = Options["graphHeight"] / 2
		middleHeight = Options["graphHeight"] / 4
		ac.glBegin(acsys.GL.Lines)
		# bottom - red
		ac.glColor4f(1, 0, 0, 1)
		ac.glVertex2f(x + dx1, y + halfHeight)
		ac.glVertex2f(x + dx2, y + halfHeight)
		# right bottom - red
		ac.glVertex2f(x + dx2, y + halfHeight)
		ac.glVertex2f(x + dx2, y + middleHeight)
		# right top - green to yellow
		ac.glColor4f(0, 1, 0, 1)
		ac.glVertex2f(x + dx2, y + middleHeight)
		ac.glColor4f(1, 1, 0, 1)
		ac.glVertex2f(x + dx2, y - halfHeight)
		# top - yellow
		ac.glVertex2f(x + dx2, y - halfHeight)
		ac.glVertex2f(x + dx1, y - halfHeight)
		# left top - yellow to green
		ac.glVertex2f(x + dx1, y - halfHeight)
		ac.glColor4f(0, 1, 0, 1)
		ac.glVertex2f(x + dx1, y + middleHeight)
		# left bottom - red
		ac.glColor4f(1, 0, 0, 1)
		ac.glVertex2f(x + dx1, y + middleHeight)
		ac.glVertex2f(x + dx1, y + halfHeight)
		# middle - red
		ac.glVertex2f(x + dx1, y + middleHeight)
		ac.glVertex2f(x + dx2, y + middleHeight)
		ac.glEnd()

		sumPos = 1
		sumNeg = -1
		countPos = 1
		countNeg = 1

		scaleNeg = -(halfHeight + middleHeight) / self.minVal
		scalePos = (halfHeight - middleHeight) / self.maxVal

		for i in range(len(self.serie)):
			#~ color = getColor(self.serie[i])
			color = self.serie[i]["color"]
			h = max(min(self.maxVal,self.serie[i]["value"]),self.minVal)
			if self.serie[i]["value"] > 0:
				sumPos += self.serie[i]["value"]
				countPos += 1
				h *= scalePos
				ac.glColor4f(1, 0, 0, 1)
			else:
				sumNeg += self.serie[i]["value"]
				countNeg += 1
				h *= scaleNeg
				ac.glColor4f(1, 1, 1, 1)
			ac.glBegin(acsys.GL.Lines)
			ac.glVertex2f(x + dx2 - i * f, y + middleHeight - 1)
			ac.glColor4f(color['r'], color['g'], color['b'], color['a'])
			ac.glVertex2f(x + dx2 - i * f, y + middleHeight - 1 + h)
			ac.glEnd()

		if Options["normalize"] and len(self.serie) == Options["graphWidth"]:
			avgPos = sumPos / countPos
			avgNeg = sumNeg / countNeg
			self.maxVal = avgPos * 1.5
			self.minVal = avgNeg * 1.5
		else:
			self.minVal = Options["targetCamber"] * 1.5
			self.maxVal = 1.5


# This function gets called by AC when the Plugin is initialised
# The function has to return a string with the plugin name
def acMain(ac_version):
	global appWindow, CamberIndicators, CheckBoxes, Buttons, Options, Labels, UIData
	loadOptions()
	appWindow = ac.newApp("CamberExtravaganza")
	ac.setSize(appWindow, 200, 200)
	ac.drawBorder(appWindow, 0)
	ac.setBackgroundOpacity(appWindow, 0)
	ac.setIconPosition(appWindow, 0, -10000)

	# Only enable rendering if app is activated
	ac.addOnAppActivatedListener(appWindow, onAppActivated)
	ac.addOnAppDismissedListener(appWindow, onAppDismissed)

	# Target Camber Labels
	Labels["target"] = ac.addLabel(appWindow, "Target:")
	ac.setPosition(Labels["target"], 85, 100)
	ac.setFontSize(Labels["target"], 10)
	Labels["targetCamberF"] = ac.addLabel(appWindow, "")
	ac.setPosition(Labels["targetCamberF"], 75, 76)
	ac.setFontSize(Labels["targetCamberF"], 24)
	Labels["targetCamberR"] = ac.addLabel(appWindow, "")
	ac.setPosition(Labels["targetCamberR"], 75, 105)
	ac.setFontSize(Labels["targetCamberR"], 24)

	# Options Checkbox
	CheckBoxes["options"] = ac.addCheckBox(appWindow, "Options")
	ac.setPosition(CheckBoxes["options"], 50, 225)
	ac.addOnCheckBoxChanged(CheckBoxes["options"], checkboxHandler)

	# Option Buttons
	uidata = [
		["drawGraphs", "Draw Graphs", drawGraphsHandler],
		["normalize", "Normalize", normalizeHandler],
		["useSpectrum", "Use Spectrum", useSpectrumHandler]
	]
	x = 50
	y = 255
	dy = 30
	for d in uidata:
		Buttons[d[0]] = ac.addButton(appWindow, d[1])
		ac.setPosition(Buttons[d[0]], x, y)
		ac.setSize(Buttons[d[0]], 100, 25)
		ac.addOnClickedListener(Buttons[d[0]], d[2])
		ac.setVisible(Buttons[d[0]], 0)
		y += dy

	# Get optimal camber from files
	loadTireData()

	CamberIndicators["FL"] = CamberIndicator(appWindow, 25, 75)
	CamberIndicators["FR"] = CamberIndicator(appWindow,125, 75)
	CamberIndicators["RL"] = CamberIndicator(appWindow, 25,175)
	CamberIndicators["RR"] = CamberIndicator(appWindow,125,175)
	ac.addRenderCallback(appWindow, onFormRender)
	return "CamberExtravaganza"


def onFormRender(deltaT):
	global doRender, CamberIndicators, Options, Labels, redrawText

	if not doRender:
		return

	ac.glColor4f(0.9, 0.9, 0.9, 0.9)
	#~ ac.setText(Labels["targetCamber"], "{0:.1f}°".format(Options["targetCamber"]))

	# Suspension travel to find body position relative to tires
	radius = Options["tireRadius"]
	pixelsPerMeter = Options["tireHeight"] / radius
	w,x,y,z = ac.getCarState(0, acsys.CS.SuspensionTravel)
	dyFL = w * pixelsPerMeter
	dyFR = x * pixelsPerMeter
	dyRL = y * pixelsPerMeter
	dyRR = z * pixelsPerMeter

	# Draw front "car body"
	xFR = CamberIndicators["FR"].xPosition
	xFL = CamberIndicators["FL"].xPosition + Options["tireHeight"]
	y = CamberIndicators["FR"].yPosition - Options["tireHeight"] / 2
	yFL = y + dyFL
	yFR = y + dyFR
	h = Options["tireHeight"] / 4
	ac.glColor4f(0.9, 0.9, 0.9, 0.9)
	ac.glBegin(acsys.GL.Lines)
	ac.glVertex2f(xFL, yFL + h)
	ac.glVertex2f(xFR, yFR + h)
	ac.glVertex2f(xFR, yFR + h)
	ac.glVertex2f(xFR, yFR - h)
	ac.glVertex2f(xFR, yFR - h)
	ac.glVertex2f(xFL, yFL - h)
	ac.glVertex2f(xFL, yFL - h)
	ac.glVertex2f(xFL, yFL + h)
	ac.glEnd()

	# Draw rear "car body"
	xRR = CamberIndicators["RR"].xPosition
	xRL = CamberIndicators["RL"].xPosition + Options["tireHeight"]
	y = CamberIndicators["RR"].yPosition - Options["tireHeight"] / 2
	yRL = y + dyRL
	yRR = y + dyRR
	h = Options["tireHeight"] / 4
	ac.glColor4f(0.9, 0.9, 0.9, 0.9)
	ac.glBegin(acsys.GL.Lines)
	ac.glVertex2f(xRL, yRL + h)
	ac.glVertex2f(xRR, yRR + h)
	ac.glVertex2f(xRR, yRR + h)
	ac.glVertex2f(xRR, yRR - h)
	ac.glVertex2f(xRR, yRR - h)
	ac.glVertex2f(xRL, yRL - h)
	ac.glVertex2f(xRL, yRL - h)
	ac.glVertex2f(xRL, yRL + h)
	ac.glEnd()

	# Draw flappy gauges
	h *= 0.75
	CamberIndicators["FL"].drawTire(xFL, yFL, h, flip=True)
	CamberIndicators["FR"].drawTire(xFR, yFR, h)
	CamberIndicators["RL"].drawTire(xRL, yRL, h, flip=True)
	CamberIndicators["RR"].drawTire(xRR, yRR, h)

	# Draw history graphs
	if Options["drawGraphs"]:
		CamberIndicators["FL"].drawGraph(flip=True)
		CamberIndicators["FR"].drawGraph()
		CamberIndicators["RL"].drawGraph(flip=True)
		CamberIndicators["RR"].drawGraph()

	flC, frC, rlC, rrC = ac.getCarState(0, acsys.CS.CamberRad)
	CamberIndicators["FL"].setValue(flC, deltaT, Options["optimalCamberF"])
	CamberIndicators["FR"].setValue(frC, deltaT, Options["optimalCamberF"])
	CamberIndicators["RL"].setValue(rlC, deltaT, Options["optimalCamberR"])
	CamberIndicators["RR"].setValue(rrC, deltaT, Options["optimalCamberR"])

	# Check if tyre compound changed
	#   Do this better in the future?  Is checking for a pit stop more
	#   expensive than checking a 2-length string equality? Doubtful
	tyreCompound = ac.getCarTyreCompound(0)
	if tyreCompound != Options["tyreCompound"]:
		loadTireData()
		Options["tyreCompound"] = tyreCompound

	# Weight Front and Rear by lateral weight transfer
	filter = 0.97
	flL, frL, rlL, rrL = ac.getCarState(0, acsys.CS.Load)

	outer = max(flL, frL)
	inner = min(flL, frL)
	camberSplit = abs(flC - frC)
	weightXfer = outer / (inner + outer)
	# (2*(1-w)*D1*rad(c)-(1-2*w)*D0)/(2*D1)
	oldTargetCamber = Options["optimalCamberF"]
	Options["optimalCamberF"] = math.degrees((2 * (1 - weightXfer) * Options["dcamber1"] * math.radians(camberSplit) - (1 - 2 * weightXfer) * Options["dcamber0"]) / (2 * Options["dcamber1"]))
	Options["optimalCamberF"] = filter * oldTargetCamber + (1 - filter) * Options["optimalCamberF"]

	outer = max(rlL, rrL)
	inner = min(rlL, rrL)
	camberSplit = abs(rlC - rrC)
	weightXfer = outer / (inner + outer)
	# (2*(1-w)*D1*rad(c)-(1-2*w)*D0)/(2*D1)
	oldTargetCamber = Options["optimalCamberR"]
	Options["optimalCamberR"] = math.degrees((2 * (1 - weightXfer) * Options["dcamber1"] * math.radians(camberSplit) - (1 - 2 * weightXfer) * Options["dcamber0"]) / (2 * Options["dcamber1"]))
	Options["optimalCamberR"] = filter * oldTargetCamber + (1 - filter) * Options["optimalCamberR"]

	ac.setText(Labels["targetCamberF"], "{0:.1f}°".format(Options["optimalCamberF"]))
	ac.setText(Labels["targetCamberR"], "{0:.1f}°".format(Options["optimalCamberR"]))

	if redrawText:
		updateTextInputs()
		redrawText = False


def getColor(value, optimal):
	global Options
	color = {}
	scale = 0.5 # adjusts width of green, calculate this better later
	d = (value - optimal) * scale
	if Options["useSpectrum"] is True:
		H = max(0, min(1, 0.6 - d)) * 0.625  # 0.625 = hue 225°, #0040FF
		S = 0.9
		B = 0.9
		c = colorsys.hsv_to_rgb(H, S, B)
		color = {'r':c[0],'g':c[1],'b':c[2],'a':Options["alpha"]}

	else:
		if value > 0:
			color = {'r':1,'g':0,'b':0,'a':Options["alpha"]}
		elif d > 1.0:
			color = {'r':1,'g':0,'b':0,'a':Options["alpha"]}
		elif d > 0.5:
			color = {'r':1,'g':0.5,'b':0,'a':Options["alpha"]}
		elif d > 0.2:
			color = {'r':1,'g':1,'b':0,'a':Options["alpha"]}
		elif d > -0.2:
			color = {'r':0,'g':1,'b':0,'a':Options["alpha"]}
		elif d > -0.5:
			color = {'r':0,'g':1,'b':1,'a':Options["alpha"]}
		else:
			color = {'r':0,'g':0,'b':1,'a':Options["alpha"]}

	return color


def uiHandler(*args, name, type):
	global Options, Buttons, Labels, TextInputs, redrawText
	if type == "Button":
		Options[name] = not Options[name]
		updateButtons()
		saveOptions()
	elif type == "TextInput":
		Options[name] = args[0]
		redrawText = True
		saveOptions()
	elif type == "CheckBox":
		v = 1 if args[0] == 1 else 0
		if name == "options":
			for key, button in Buttons.items():
				ac.setVisible(button, v)
			for key, input in TextInputs.items():
				ac.setVisible(input, v)

			updateButtons()
	else:
		pass

# List of handlers, I don't know how to do this nicely
# lambdas and functools.partial crash
def checkboxHandler(name, value):
	uiHandler(value, name="options", type="CheckBox")


def drawGraphsHandler(*args):
	uiHandler(args[0], args[1], name="drawGraphs", type="Button")


def normalizeHandler(*args):
	uiHandler(args[0], args[1], name="normalize", type="Button")


def useSpectrumHandler(*args):
	uiHandler(args[0], args[1], name="useSpectrum", type="Button")


# Make sure button toggled state matches internal state
def updateButtons():
	global Options, Buttons
	for key, button in Buttons.items():
		if Options[key]:
			ac.setBackgroundColor(button, 1, 0, 0)
			ac.setFontColor(button, 1, 1, 1, 1)
			ac.setBackgroundOpacity(button, 1)
		else:
			ac.setBackgroundColor(button, 1, 1, 1)
			ac.setFontColor(button, 0, 0, 0, 1)
			ac.setBackgroundOpacity(button, 1)


# Load DCAMBERs and RADIUS
def loadTireData():
	global Options

	try:
		tyresFile = os.path.join(os.path.dirname(__file__), "tyres-data.json")
		with open(tyresFile, "r") as f:
			tyreData = json.load(f)

	except OSError:
		ac.log("CamberExtravaganza ERROR: loadTireData tyres-data.json not found")

	else:
		try:
			carName = ac.getCarName(0)
			tyreCompound = ac.getCarTyreCompound(0)
			Options["tireRadius"] = tyreData[carName][tyreCompound]["radius"]
			dcamber0 = tyreData[carName][tyreCompound]["dcamber0"]
			dcamber1 = tyreData[carName][tyreCompound]["dcamber1"]
			Options["targetCamber"] = math.degrees(dcamber0 / (2 * dcamber1))
			Options["dcamber0"] = dcamber0
			Options["dcamber1"] = dcamber1
			ac.console("Tyre data found for " + carName + " " + tyreCompound)

		except KeyError: # Doesn't exist in official, look for custom data
			try:
				tyresFile = os.path.join(os.path.dirname(__file__), "tyres-data-custom.json")
				with open(tyresFile, "r") as f:
					tyreData = json.load(f)
					Options["tireRadius"] = tyreData[carName][tyreCompound]["radius"]
					dcamber0 = tyreData[carName][tyreCompound]["dcamber0"]
					dcamber1 = tyreData[carName][tyreCompound]["dcamber1"]
					Options["targetCamber"] = math.degrees(dcamber0 / (2 * dcamber1))
					Options["dcamber0"] = dcamber0
					Options["dcamber1"] = dcamber1

			except (OSError, KeyError) as e:
				Options["tireRadius"] = 1
				Options["targetCamber"] = 999
				Options["dcamber0"] = 999
				Options["dcamber1"] = -999
				ac.log("CamberExtravaganza ERROR: loadTireData: No custom tyre data found for this car")

			else:
				ac.console("Custom tyre data found for " + carName + " " + tyreCompound)


def saveOptions():
	global Options, CheckBoxes
	optionsFile = os.path.join(os.path.dirname(__file__), 'options.dat')
	with open(optionsFile, 'wb') as handle:
		data = {}
		for key,option in Options.items():
			if key in SavableOptions:
				data[key] = option
		pickle.dump(data, handle, protocol=pickle.HIGHEST_PROTOCOL)


def loadOptions():
	global Options
	try:
		optionsFile = os.path.join(os.path.dirname(__file__), 'options.dat')
		with open(optionsFile, 'rb') as handle:
			data = pickle.load(handle)
			for key,datum in data.items():
				if key in SavableOptions:
					Options[key] = datum
	except IOError:
		ac.log("CamberExtravaganza ERROR: loadOptions IOError")


def onAppActivated():
	global doRender
	doRender = True


def onAppDismissed():
	global doRender
	doRender = False
