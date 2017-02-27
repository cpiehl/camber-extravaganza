##############################################################
# Camber Extravaganza!
# App for showing camber in real time
# Useful for tuning?
#
# TODO:
#   - Separate front and rear target camber
#   - Make log scale better
#   - change deque maxlen when graphwidth changed
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
#       - UI code cleanup
#############################################################

import ac
import acsys
import collections
import colorsys
import math
import os
import pickle

appWindow = 0
CamberIndicators = {}
optionsCheckBox = 0
CheckBoxes = {}
Buttons = {}
TextInputs = {}
Labels = {}
redrawText = False
Options = {
	"drawGraphs": False,
	"showAverage": False,
	"normalize": False,
	"useSpectrum": True,
	"size": 50,        # flapper length
	"radScale": 10,    # flappiness ratio
	"peakTime": 2,     # seconds
	"graphWidth": 150, # in pixels, also the number of frames of data to display
	"graphHeight": 60, # in pixels
	"targetCamber": -3 # degrees
}

class CamberIndicator:
	def __init__(self, app, x, y):
		global Options
		self.xPosition = x
		self.yPosition = y
		self.value = 0
		self.peakValue = 0
		self.peakTime = 0
		self.color = {'r':1,'g':1,'b':1,'a':1}
		self.serie = collections.deque(maxlen=Options["graphWidth"])
		self.minVal = -4.5
		self.maxVal = 1.5

		self.valueLabel = ac.addLabel(appWindow, "0.0°")
		ac.setPosition(self.valueLabel, x, y)
		self.peakValueLabel = ac.addLabel(appWindow, "0.0°")
		ac.setPosition(self.peakValueLabel, x, y + 18)


	def setValue(self, value, deltaT):
		global Options
		self.value = value
		deg = math.degrees(self.value)
		ac.setText(self.valueLabel,"{0:.3f}°".format(deg))

		self.serie.append(deg)

		self.color = getColor(deg)

		if Options["showAverage"]:
			self.peakValue = sum(self.serie) / len(self.serie)
			ac.setFontColor(self.peakValueLabel,
				self.color['r'],
				self.color['g'],
				self.color['b'],
				self.color['a']
			)
			ac.setText(self.peakValueLabel,"{0:.3f}°".format(self.peakValue))
		else:
			self.peakTime -= deltaT
			if self.peakTime <= 0:
				self.peakValue = value

			if value >= self.peakValue:
				self.peakTime = Options["peakTime"]
				self.peakValue = value
				ac.setFontColor(self.peakValueLabel,
					self.color['r'],
					self.color['g'],
					self.color['b'],
					self.color['a']
				)
				ac.setText(self.peakValueLabel,"{0:.3f}°".format(math.degrees(self.peakValue)))


	def drawGauge(self, flip=False):
		global Options
		ac.glColor4f(
			self.color['r'],
			self.color['g'],
			self.color['b'],
			self.color['a']
		)

		x = self.xPosition
		y = self.yPosition
		rad = self.value * Options["radScale"]
		size = Options["size"]
		if flip:
			x += 50
			rad = math.pi - rad

		ac.glBegin(acsys.GL.Lines)
		ac.glVertex2f(x, y)
		ac.glVertex2f(x+size*math.cos(rad), y+size*math.sin(rad))
		ac.glEnd()


	def drawGraph(self, flip=False):
		global Options
		x = self.xPosition
		y = self.yPosition + 5
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
			color = getColor(self.serie[i])
			h = max(min(self.maxVal,self.serie[i]),self.minVal)
			if self.serie[i] > 0:
				sumPos += self.serie[i]
				countPos += 1
				h *= scalePos
				ac.glColor4f(1, 0, 0, 1)
			else:
				sumNeg += self.serie[i]
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
			self.maxVal = 1.5
			self.minVal = -4.5


# This function gets called by AC when the Plugin is initialised
# The function has to return a string with the plugin name
def acMain(ac_version):
	global appWindow, CamberIndicators, CheckBoxes, Buttons, Options, TextInputs, Labels
	loadOptions()
	appWindow = ac.newApp("CamberExtravaganza")
	ac.setSize(appWindow, 200, 200)
	ac.drawBorder(appWindow, 0)
	ac.setBackgroundOpacity(appWindow, 0)
	ac.setIconPosition(appWindow, 0, -10000)

	# Options Checkbox
	optionsCheckBox = ac.addCheckBox(appWindow, "Options")
	ac.setPosition(optionsCheckBox, 10, 200)
	ac.addOnCheckBoxChanged(optionsCheckBox, checkboxHandler)

	# Option Buttons
	uidata = [
		["drawGraphs", "Draw Graphs", drawGraphsHandler],
		["normalize", "Normalize", normalizeHandler],
		["showAverage", "Show Average", showAverageHandler],
		["useSpectrum", "Use Spectrum", useSpectrumHandler]
	]
	y = 230
	dy = 30
	for d in uidata:
		Buttons[d[0]] = ac.addButton(appWindow, d[1])
		ac.setPosition(Buttons[d[0]], 10, y)
		ac.setSize(Buttons[d[0]], 100, 25)
		ac.addOnClickedListener(Buttons[d[0]], d[2])
		ac.setVisible(Buttons[d[0]], 0)
		y += dy

	# Option TextInputs and Labels
	uidata = [
		["Target Camber", targetInputHandler],
		["Flappiness", radScaleInputHandler],
		["Peak Time", peakTimeInputHandler],
		["Graph Width", graphWidthInputHandler],
		["Graph Height", graphHeightInputHandler]
	]
	y = 200
	dy = 30
	for d in uidata:
		TextInputs[d[0]] = ac.addTextInput(appWindow, d[0])
		ac.setPosition(TextInputs[d[0]], 160, y)
		ac.setSize(TextInputs[d[0]], 50, 25)
		ac.addOnValidateListener(TextInputs[d[0]], d[1])
		Labels[d[0]] = ac.addLabel(appWindow, d[0])
		ac.setPosition(Labels[d[0]], 220, y)
		ac.setVisible(TextInputs[d[0]], 0)
		ac.setVisible(Labels[d[0]], 0)
		y += dy

	CamberIndicators["FL"] = CamberIndicator(appWindow, 25, 50)
	CamberIndicators["FR"] = CamberIndicator(appWindow,125, 50)
	CamberIndicators["RL"] = CamberIndicator(appWindow, 25,150)
	CamberIndicators["RR"] = CamberIndicator(appWindow,125,150)
	ac.addRenderCallback(appWindow, onFormRender)
	return "CamberExtravaganza"


def onFormRender(deltaT):
	global CamberIndicators, Options, redrawText
	# Draw flappy gauges
	CamberIndicators["FL"].drawGauge(flip=True)
	CamberIndicators["FR"].drawGauge()
	CamberIndicators["RL"].drawGauge(flip=True)
	CamberIndicators["RR"].drawGauge()
	# Draw history graphs
	if Options["drawGraphs"]:
		CamberIndicators["FL"].drawGraph(flip=True)
		CamberIndicators["FR"].drawGraph()
		CamberIndicators["RL"].drawGraph(flip=True)
		CamberIndicators["RR"].drawGraph()
	w,x,y,z = ac.getCarState(0, acsys.CS.CamberRad)
	CamberIndicators["FL"].setValue(w, deltaT)
	CamberIndicators["FR"].setValue(x, deltaT)
	CamberIndicators["RL"].setValue(y, deltaT)
	CamberIndicators["RR"].setValue(z, deltaT)
	if redrawText:
		updateTextInputs()
		redrawText = False


def getColor(value):
	global Options
	color = {}
	scale = 0.5 # 0.5 / scale = max +/- range
	d = (value - Options["targetCamber"]) * scale
	if Options["useSpectrum"] is True:
		H = max(0, min(1, 0.5 - d)) * 0.625  # 0.625 = hue 225°, #0040FF
		S = 0.9
		B = 0.9
		c = colorsys.hsv_to_rgb(H, S, B)
		color = {'r':c[0],'g':c[1],'b':c[2],'a':1}

	else:
		if value > 0:
			color = {'r':1,'g':0,'b':0,'a':1}
		elif d > 1.0:
			color = {'r':1,'g':0,'b':0,'a':1}
		elif d > 0.5:
			color = {'r':1,'g':0.5,'b':0,'a':1}
		elif d > 0.2:
			color = {'r':1,'g':1,'b':0,'a':1}
		elif d > -0.2:
			color = {'r':0,'g':1,'b':0,'a':1}
		elif d > -0.5:
			color = {'r':0,'g':1,'b':1,'a':1}
		else:
			color = {'r':0,'g':0,'b':1,'a':1}

	return color


def targetInputHandler(value):
	global Options, TextInputs, redrawText
	try:
		Options["targetCamber"] = float(value)
		redrawText = True
		saveOptions()
	except ValueError:
		pass

def radScaleInputHandler(value):
	global Options, TextInputs, redrawText
	try:
		Options["radScale"] = float(value)
		redrawText = True
		saveOptions()
	except ValueError:
		pass

def peakTimeInputHandler(value):
	global Options, TextInputs, redrawText
	try:
		Options["peakTime"] = float(value)
		redrawText = True
		saveOptions()
	except ValueError:
		pass

def graphWidthInputHandler(value):
	global Options, TextInputs, redrawText
	try:
		Options["graphWidth"] = int(value)
		redrawText = True
		saveOptions()
	except ValueError:
		pass

def graphHeightInputHandler(value):
	global Options, TextInputs, redrawText
	try:
		Options["graphHeight"] = int(value)
		redrawText = True
		saveOptions()
	except ValueError:
		pass


def checkboxHandler(name, value):
	global Options, Buttons, TextInputs, Labels
	v = 1 if value == 1 else 0
	if name == "Options":
		for key, button in Buttons.items():
			ac.setVisible(button, v)
		for key, input in TextInputs.items():
			ac.setVisible(input, v)
		for key, label in Labels.items():
			ac.setVisible(label, v)
		updateButtons()
		updateTextInputs()


def drawGraphsHandler(x, y):
	global Options, Buttons
	Options["drawGraphs"] = not Options["drawGraphs"]
	updateButtons()
	saveOptions()


def normalizeHandler(x, y):
	global Options, Buttons
	Options["normalize"] = not Options["normalize"]
	updateButtons()
	saveOptions()


def showAverageHandler(x, y):
	global Options, Buttons
	Options["showAverage"] = not Options["showAverage"]
	updateButtons()
	saveOptions()


def useSpectrumHandler(x, y):
	global Options, Buttons
	Options["useSpectrum"] = not Options["useSpectrum"]
	updateButtons()
	saveOptions()


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


def updateTextInputs():
	global Options, TextInputs
	ac.setText(TextInputs["Target Camber"], str(Options["targetCamber"]))
	ac.setText(TextInputs["Flappiness"], str(Options["radScale"]))
	ac.setText(TextInputs["Peak Time"], str(Options["peakTime"]))
	ac.setText(TextInputs["Graph Width"], str(Options["graphWidth"]))
	ac.setText(TextInputs["Graph Height"], str(Options["graphHeight"]))


def saveOptions():
	global Options, CheckBoxes
	optionsFile = os.path.join(os.path.dirname(__file__), 'options.dat')
	with open(optionsFile, 'wb') as handle:
		pickle.dump(Options, handle, protocol=pickle.HIGHEST_PROTOCOL)

def loadOptions():
	global Options
	try:
		optionsFile = os.path.join(os.path.dirname(__file__), 'options.dat')
		with open(optionsFile, 'rb') as handle:
			Options.update(pickle.load(handle))
	except IOError:
		pass
