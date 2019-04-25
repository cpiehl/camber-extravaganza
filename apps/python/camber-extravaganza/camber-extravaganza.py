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
# V2.0	- Separate front and rear tyre data
#		- Reworked optimal camber equation?
#
# V2.1	- Fix optimal camber equation, remove extra rad()
#		- Switch to tyres_data folder, load any JSON
#
# V2.2	- Add "Show Delta" mode
#		- Fix divide by zero when dcamber1 = 0
#
# V2.3	- Logging
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
import platform
import sys
import time
import traceback

if platform.architecture()[0] == "64bit":
    libdir = 'third_party/lib64'
else:
    libdir = 'third_party/lib'
sys.path.insert(0, os.path.join(os.path.dirname(__file__), libdir))
os.environ['PATH'] = os.environ['PATH'] + ";."

from third_party.sim_info import info

appWindow = 0
CamberIndicators = {}
CheckBoxes = {}
Buttons = {}
TextInputs = {}
Labels = {}
redrawText = False
customFont = "Consolas"
Options = {
	"drawGraphs": False,
	"normalize": False,
	"useSpectrum": True,
	"showDelta": False,
	"alpha": 0.5,        # graph alpha
	"tireHeight": 50,    # tire height
	"radScale": 10,      # scale flapper deflection to this at 2*peak grip
	"graphWidth": 150,   # in pixels, also the number of frames of data to display
	"graphHeight": 85,   # in pixels
	"targetCamberF": 999, # degrees
	"targetCamberR": 999, # degrees
	"optimalCamberF": 999, # degrees
	"optimalCamberR": 999, # degrees
	"dcamber0F": 999,     # initial
	"dcamber1F": -999,    # initial
	"dcamber0R": 999,     # initial
	"dcamber1R": -999,    # initial
	"LS_EXPYF": 1,        # tire load sensitivity exponent
	"LS_EXPYR": 1,        # tire load sensitivity exponent
	"tyreCompound": "",  # short name
	"carNotFound": False,
	"enableLogging": False,
	"logFileName": "",
	"logData": []
}
SavableOptions = [ # Only save these to file
	"drawGraphs",
	"normalize",
	"useSpectrum",
	"showDelta",
	"enableLogging"
]
doRender = True

class CamberIndicator:
	def __init__(self, app, x, y):
		global Options

		try:
			self.xPosition = x
			self.yPosition = y
			self.value = 0
			self.avgValue = 0
			self.color = {'r':1,'g':1,'b':1,'a':1}
			self.serie = collections.deque(maxlen=Options["graphWidth"])
			self.minVal = 6
			self.maxVal = 1.5

			self.valueLabel = ac.addLabel(appWindow, "0.0°")
			ac.setPosition(self.valueLabel, x, y)
			self.avgValueLabel = ac.addLabel(appWindow, "0.0°")
			ac.setPosition(self.avgValueLabel, x, y + 18)
		except Exception:
			ac.log("CamberExtravaganza ERROR: CamberIndicator.__init__(): %s" % traceback.format_exc())



	def setValue(self, value, deltaT, optimal):
		global Options

		try:
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
		except Exception:
			ac.log("CamberExtravaganza ERROR: setValue(): %s" % traceback.format_exc())



	def drawTire(self, suspX, suspY, suspH, flip=False):
		global Options

		try:
			x = self.xPosition + 25
			y = self.yPosition
			#~ rad = self.value * Options["radScale"]
			#~ rad = self.value * Options["radScale"] / (2 * -Options["targetCamber"])
			rad = self.value
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
		except Exception:
			ac.log("CamberExtravaganza ERROR: drawTire(): %s" % traceback.format_exc())



	def drawGraph(self, flip=False):
		global Options

		try:
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
				if 0 != Options["targetCamberF"]:
					self.minVal = Options["targetCamberF"] * 1.5
				else:
					self.minVal = 6
				self.maxVal = 1.5

		except Exception:
			ac.log("CamberExtravaganza ERROR: drawGraph(): %s" % traceback.format_exc())


# This function gets called by AC when the Plugin is initialised
# The function has to return a string with the plugin name
def acMain(ac_version):
	global appWindow, CamberIndicators, CheckBoxes, Buttons, Options, Labels, UIData

	try:
		loadOptions()
		appWindow = ac.newApp("CamberExtravaganza")
		ac.setSize(appWindow, 200, 200)
		ac.drawBorder(appWindow, 0)
		ac.setBackgroundOpacity(appWindow, 0)
		ac.setIconPosition(appWindow, 0, -10000)

		# Only enable rendering if app is activated
		ac.addOnAppActivatedListener(appWindow, onAppActivated)
		ac.addOnAppDismissedListener(appWindow, onAppDismissed)

		# Custom monospace font
		ac.initFont(0, customFont, 0, 0)

		# Target Camber Labels
		Labels["target"] = ac.addLabel(appWindow, "Target:")
		if Options["showDelta"]:
			ac.setText(Labels["target"], "Delta:")
		else:
			ac.setText(Labels["target"], "Target:")
		ac.setPosition(Labels["target"], 85, 100)
		ac.setCustomFont(Labels["target"], customFont, 0, 0)
		ac.setFontSize(Labels["target"], 10)
		Labels["targetCamberF"] = ac.addLabel(appWindow, "")
		ac.setPosition(Labels["targetCamberF"], 65, 76)
		ac.setCustomFont(Labels["targetCamberF"], customFont, 0, 0)
		ac.setFontSize(Labels["targetCamberF"], 24)
		Labels["targetCamberR"] = ac.addLabel(appWindow, "")
		ac.setPosition(Labels["targetCamberR"], 65, 105)
		ac.setCustomFont(Labels["targetCamberR"], customFont, 0, 0)
		ac.setFontSize(Labels["targetCamberR"], 24)

		# Options Checkbox
		CheckBoxes["options"] = ac.addCheckBox(appWindow, "Options")
		ac.setPosition(CheckBoxes["options"], 50, 225)
		ac.addOnCheckBoxChanged(CheckBoxes["options"], checkboxHandler)

		# Option Buttons
		uidata = [
			["drawGraphs", "Draw Graphs", drawGraphsHandler],
			["normalize", "Normalize", normalizeHandler],
			["useSpectrum", "Use Spectrum", useSpectrumHandler],
			["showDelta", "Show Delta", showDeltaHandler],
			["enableLogging", "Enable Logging", enableLoggingHandler]
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

		CamberIndicators["FL"] = CamberIndicator(appWindow,  15,  75)
		CamberIndicators["FR"] = CamberIndicator(appWindow, 135,  75)
		CamberIndicators["RL"] = CamberIndicator(appWindow,  15, 175)
		CamberIndicators["RR"] = CamberIndicator(appWindow, 135, 175)

		initLogging()

		ac.addRenderCallback(appWindow, onFormRender)

	except Exception:
		ac.log("CamberExtravaganza ERROR: acMain(): %s" % traceback.format_exc())

	return "CamberExtravaganza"


def onFormRender(deltaT):
	global CamberIndicators, Options, Labels, redrawText

	try:
		if not doRender:
			return

		ac.glColor4f(0.9, 0.9, 0.9, 0.9)
		#~ ac.setText(Labels["targetCamberF"], "{0:.1f}°".format(Options["targetCamber"]))

		# Suspension travel to find body position relative to tires
		#~ pixelsPerMeterF = Options["tireHeight"] / Options["tireRadiusF"]
		#~ pixelsPerMeterR = Options["tireHeight"] / Options["tireRadiusR"]
		pixelsPerMeterF = Options["tireHeight"] / info.static.tyreRadius[0]
		pixelsPerMeterR = Options["tireHeight"] / info.static.tyreRadius[2]
		w,x,y,z = ac.getCarState(0, acsys.CS.SuspensionTravel)
		dyFL = w * pixelsPerMeterF
		dyFR = x * pixelsPerMeterF
		dyRL = y * pixelsPerMeterR
		dyRR = z * pixelsPerMeterR

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
		tyreCompound = ac.getCarTyreCompound(0)
		if tyreCompound != Options["tyreCompound"]:
			loadTireData()
			Options["tyreCompound"] = tyreCompound

		# Weight Front and Rear by lateral weight transfer
		filter = 0.97
		flL, frL, rlL, rrL = ac.getCarState(0, acsys.CS.Load)

		outer = max(0.001, flL, frL)
		inner = min(flL, frL)
		cf_outer = CamberIndicators["FL"].avgValue if outer == flL else CamberIndicators["FR"].avgValue
		camberSplit = abs(flC - frC)
		# DY_LS_FL = DY_REF * pow(TIRE_LOAD_FL / FZ0, LS_EXPY)
		ls_outer = pow(outer, Options["LS_EXPYF"])
		ls_inner = pow(inner, Options["LS_EXPYF"])
		weightXfer = ls_outer / (ls_inner + ls_outer)
		# (2*(1-w)*D1*rad(c)-(1-2*w)*D0)/(2*D1)
		oldTargetCamber = Options["optimalCamberF"]
		#~ Options["optimalCamberF"] = math.degrees((2 * (1 - weightXfer) * Options["dcamber1F"] * math.radians(camberSplit) - (1 - 2 * weightXfer) * Options["dcamber0F"]) / (2 * Options["dcamber1F"]))
		Options["optimalCamberF"] = optimalCamber(weightXfer, Options["dcamber0F"], Options["dcamber1F"], camberSplit)
		Options["optimalCamberF"] = filter * oldTargetCamber + (1 - filter) * Options["optimalCamberF"]

		outer = max(0.001, rlL, rrL)
		inner = min(rlL, rrL)
		cr_outer = CamberIndicators["RL"].avgValue if outer == rlL else CamberIndicators["RR"].avgValue
		camberSplit = abs(rlC - rrC)
		# DY_LS_FL = DY_REF * pow(TIRE_LOAD_FL / FZ0, LS_EXPY)
		ls_outer = pow(outer, Options["LS_EXPYR"])
		ls_inner = pow(inner, Options["LS_EXPYR"])
		weightXfer = ls_outer / (ls_inner + ls_outer)
		# (2*(1-w)*D1*rad(c)-(1-2*w)*D0)/(2*D1)
		oldTargetCamber = Options["optimalCamberR"]
		#~ Options["optimalCamberR"] = math.degrees((2 * (1 - weightXfer) * Options["dcamber1R"] * math.radians(camberSplit) - (1 - 2 * weightXfer) * Options["dcamber0R"]) / (2 * Options["dcamber1R"]))
		Options["optimalCamberR"] = optimalCamber(weightXfer, Options["dcamber0R"], Options["dcamber1R"], camberSplit)
		Options["optimalCamberR"] = filter * oldTargetCamber + (1 - filter) * Options["optimalCamberR"]

		degFront = Options["optimalCamberF"]
		degRear = Options["optimalCamberR"]
		if Options["showDelta"]:
			degFront -= cf_outer
			degRear -= cr_outer
		ac.setText(Labels["targetCamberF"], "{0:+.1f}°".format(degFront))
		ac.setText(Labels["targetCamberR"], "{0:+.1f}°".format(degRear))

		if redrawText:
			updateTextInputs()
			redrawText = False

		if Options["enableLogging"]:
			laptime = ac.getCarState(0, acsys.CS.LapTime)
			lapcount = ac.getCarState(0, acsys.CS.LapCount)
			# NormalizedSplinePosition lets you compare the same corners independent of lap time
			nsp = ac.getCarState(0, acsys.CS.NormalizedSplinePosition)
			Options["logData"].append(", ".join((str(n) for n in (lapcount, nsp, laptime, flC, frC, rlC, rrC, degFront, degRear))) + "\n")
			if len(Options["logData"]) >= 1000:
				appendLogData()
				Options["logData"] = []

	except Exception:
		ac.log("CamberExtravaganza ERROR: onFormRender(): %s" % traceback.format_exc())


def appendLogData():
	if len(Options["logData"]) > 0:
		with open(Options["logFileName"], "a") as f:
			for ld in Options["logData"]:
				f.write(ld)


def initLogging():
	Options["logData"] = newLogData()
	Options["logFileName"] = os.path.join(os.path.dirname(__file__), "camber_log-%s.csv" % (time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())))


def newLogData():
	return [ "Lap, NSP, Lap Time, FL Camber, FR Camber, RL Camber, RR Camber, F Target, R Target\n" ]


def optimalCamber(weightXfer, dcamber0, dcamber1, camberSplit):
	if Options["carNotFound"]:
		return 99
	if dcamber0 == 0 or dcamber1 == 0:
		return 0
	return math.degrees((2 * (1 - weightXfer) * dcamber1 * camberSplit - (1 - 2 * weightXfer) * dcamber0) / (2 * dcamber1))


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


def showDeltaHandler(*args):
	uiHandler(args[0], args[1], name="showDelta", type="Button")
	if Options["showDelta"]:
		ac.setText(Labels["target"], "Delta:")
	else:
		ac.setText(Labels["target"], "Target:")


def enableLoggingHandler(*args):
	uiHandler(args[0], args[1], name="enableLogging", type="Button")
	if Options["enableLogging"]:
		initLogging()
	else:
		appendLogData()


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


def parseTyreData(carName, tyreCompound, tyreData):
	global Options

	try:
		dcamber0F = tyreData[carName]['FRONT'][tyreCompound]["DCAMBER_0"]
		dcamber1F = tyreData[carName]['FRONT'][tyreCompound]["DCAMBER_1"]
		dcamber0R = tyreData[carName]['REAR'][tyreCompound]["DCAMBER_0"]
		dcamber1R = tyreData[carName]['REAR'][tyreCompound]["DCAMBER_1"]
		if dcamber1F == 0:
			Options["targetCamberF"] = 0
		else:
			Options["targetCamberF"] = math.degrees(dcamber0F / (2 * dcamber1F))
		if dcamber1R == 0:
			Options["targetCamberR"] = 0
		else:
			Options["targetCamberR"] = math.degrees(dcamber0R / (2 * dcamber1R))
		Options["dcamber0F"] = dcamber0F
		Options["dcamber1F"] = dcamber1F
		Options["dcamber0R"] = dcamber0R
		Options["dcamber1R"] = dcamber1R
		Options["LS_EXPYF"] = tyreData[carName]['FRONT'][tyreCompound]["LS_EXPY"]
		Options["LS_EXPYR"] = tyreData[carName]['REAR'][tyreCompound]["LS_EXPY"]

		ac.log("CamberExtravaganza: Tyre data found for " + carName + " " + tyreCompound)

	except KeyError:
		Options["targetCamberF"] = -999
		Options["targetCamberR"] = -999
		Options["dcamber0F"] = 999
		Options["dcamber1F"] = -999
		Options["dcamber0R"] = 999
		Options["dcamber1R"] = -999
		Options["LS_EXPYF"] = 1
		Options["LS_EXPYR"] = 1
		Options["carNotFound"] = True

		ac.setText(Labels["target"], "Unrecognized Car")
		ac.log("CamberExtravaganza ERROR: parseTyreData: No tyre data found for car: '" + carName + "'")


# Load DCAMBERs and RADIUS
def loadTireData():
	global Options
	tyreDataPath = os.path.join(os.path.dirname(__file__), "tyres_data")
	tyreData = {}
	namelist = ''
	for td in os.listdir(tyreDataPath):
		if td.endswith('.json'):
			with open(os.path.join(tyreDataPath, td), 'r') as f:
				try:
					newData = json.load(f)
				except ValueError as e:
					ac.log("CamberExtravaganza ERROR: Invalid JSON: " + td)
				else:
					tyreData.update(newData)
					namelist = namelist + td + ', '

	ac.log(namelist)

	carName = ac.getCarName(0)
	tyreCompound = ac.getCarTyreCompound(0)
	#~ tyreCompound = info.graphics.tyreCompound

	ac.log(carName + ' ' + tyreCompound + ' compound')

	parseTyreData(carName, tyreCompound, tyreData)


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


def onAppActivated(self):
	global Options
	doRender = True
	initLogging()


def onAppDismissed(self):
	global Options
	doRender = False
	appendLogData()


def acShutdown():
	appendLogData()
