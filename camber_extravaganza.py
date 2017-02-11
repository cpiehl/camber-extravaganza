##############################################################
# Camber Extravaganza!
# App for showing camber in real time
# Useful for tuning?
#
# TODO:
#   - Make text inputs update themselves properly
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
#############################################################

import ac
import acsys
import collections
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
Options = {
	"drawGraphs": False,
	"logscale": False,
	"normalize": False,
	"useSpectrum": False,
	"size": 50,        # flapper length
	"radScale": 10,    # flappiness ratio
	"peakTime": 2,     # seconds
	"graphWidth": 150, # in pixels, also the number of frames of data to display
	"graphHeight": 60  # in pixels
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
		self.minValLog1p = math.log1p(-self.minVal)
		self.maxValLog1p = math.log1p(self.maxVal)

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
		if Options["logscale"]:
			scaleNeg = -(halfHeight + middleHeight) / self.minValLog1p
			scalePos = (halfHeight - middleHeight) / self.maxValLog1p
		else:
			scaleNeg = -(halfHeight + middleHeight) / self.minVal
			scalePos = (halfHeight - middleHeight) / self.maxVal
		for i in range(len(self.serie)):
			color = getColor(self.serie[i])
			h = max(min(self.maxVal,self.serie[i]),self.minVal)
			if Options["logscale"]:
				h = math.log1p(math.fabs(h))
			if self.serie[i] > 0:
				sumPos += self.serie[i]
				countPos += 1
				h *= scalePos
			else:
				sumNeg += self.serie[i]
				countNeg += 1
				h *= scaleNeg
			ac.glBegin(acsys.GL.Lines)
			ac.glColor4f(color['r'], color['g'], color['b'], color['a'])
			ac.glVertex2f(x + dx2 - i * f, y + middleHeight - 1)
			ac.glVertex2f(x + dx2 - i * f, y + middleHeight - 1 + h)
			ac.glEnd()

		if Options["normalize"] and len(self.serie) == Options["graphWidth"]:
			avgPos = sumPos / countPos
			avgNeg = sumNeg / countNeg
			self.maxVal = avgPos * 1.5
			self.minVal = avgNeg * 1.5
			self.minValLog1p = math.log1p(-self.minVal)
			self.maxValLog1p = math.log1p(self.maxVal)
		else:
			self.maxVal = 1.5
			self.minVal = -4.5
			self.minValLog1p = math.log1p(-self.minVal)
			self.maxValLog1p = math.log1p(self.maxVal)


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


	optionsCheckBox = ac.addCheckBox(appWindow, "Options")
	ac.setPosition(optionsCheckBox, 10, 200)
	ac.addOnCheckBoxChanged(optionsCheckBox, checkboxHandler)
	Buttons["drawGraphs"] = ac.addButton(appWindow, "Draw Graphs")
	ac.setPosition(Buttons["drawGraphs"], 10, 230)
	ac.setSize(Buttons["drawGraphs"], 100, 25)
	ac.addOnClickedListener(Buttons["drawGraphs"], drawGraphsHandler)
	Buttons["normalize"] = ac.addButton(appWindow, "Normalize")
	ac.setPosition(Buttons["normalize"], 10, 260)
	ac.setSize(Buttons["normalize"], 100, 25)
	ac.addOnClickedListener(Buttons["normalize"], normalizeHandler)
	Buttons["logscale"] = ac.addButton(appWindow, "Log Scale")
	ac.setPosition(Buttons["logscale"], 10, 290)
	ac.setSize(Buttons["logscale"], 100, 25)
	ac.addOnClickedListener(Buttons["logscale"], logscaleHandler)
	Buttons["useSpectrum"] = ac.addButton(appWindow, "Use Spectrum")
	ac.setPosition(Buttons["useSpectrum"], 10, 320)
	ac.setSize(Buttons["useSpectrum"], 100, 25)
	ac.addOnClickedListener(Buttons["useSpectrum"], useSpectrumHandler)

	TextInputs["Flapper Size"] = ac.addTextInput(appWindow, "Flapper Size")
	ac.setPosition(TextInputs["Flapper Size"], 160, 200)
	ac.setSize(TextInputs["Flapper Size"], 50, 25)
	ac.addOnValidateListener(TextInputs["Flapper Size"], sizeInputHandler)
	TextInputs["Flappiness"] = ac.addTextInput(appWindow, "Flappiness")
	ac.setPosition(TextInputs["Flappiness"], 160, 230)
	ac.setSize(TextInputs["Flappiness"], 50, 25)
	ac.addOnValidateListener(TextInputs["Flappiness"], radScaleInputHandler)
	TextInputs["Peak Time"] = ac.addTextInput(appWindow, "Peak Time")
	ac.setPosition(TextInputs["Peak Time"], 160, 260)
	ac.setSize(TextInputs["Peak Time"], 50, 25)
	ac.addOnValidateListener(TextInputs["Peak Time"], peakTimeInputHandler)
	TextInputs["Graph Width"] = ac.addTextInput(appWindow, "Graph Width")
	ac.setPosition(TextInputs["Graph Width"], 160, 290)
	ac.setSize(TextInputs["Graph Width"], 50, 25)
	ac.addOnValidateListener(TextInputs["Graph Width"], graphWidthInputHandler)
	TextInputs["Graph Height"] = ac.addTextInput(appWindow, "Graph Height")
	ac.setPosition(TextInputs["Graph Height"], 160, 320)
	ac.setSize(TextInputs["Graph Height"], 50, 25)
	ac.addOnValidateListener(TextInputs["Graph Height"], graphHeightInputHandler)

	Labels["Flapper Size"] = ac.addLabel(appWindow, "Flapper Size")
	ac.setPosition(Labels["Flapper Size"], 220, 200)
	Labels["Flappiness"] = ac.addLabel(appWindow, "Flappiness")
	ac.setPosition(Labels["Flappiness"], 220, 230)
	Labels["Peak Time"] = ac.addLabel(appWindow, "Peak Time")
	ac.setPosition(Labels["Peak Time"], 220, 260)
	Labels["Graph Width"] = ac.addLabel(appWindow, "Graph Width")
	ac.setPosition(Labels["Graph Width"], 220, 290)
	Labels["Graph Height"] = ac.addLabel(appWindow, "Graph Height")
	ac.setPosition(Labels["Graph Height"], 220, 320)

	for key, button in Buttons.items():
		ac.setVisible(button, 0)
	for key, input in TextInputs.items():
		ac.setVisible(input, 0)
	for key, label in Labels.items():
		ac.setVisible(label, 0)

	CamberIndicators["FL"] = CamberIndicator(appWindow, 25, 50)
	CamberIndicators["FR"] = CamberIndicator(appWindow,125, 50)
	CamberIndicators["RL"] = CamberIndicator(appWindow, 25,150)
	CamberIndicators["RR"] = CamberIndicator(appWindow,125,150)
	ac.addRenderCallback(appWindow, onFormRender)
	return "CamberExtravaganza"


def onFormRender(deltaT):
	global CamberIndicators, Options
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


def getColor(value):
	global Options
	color = {}
	if Options["useSpectrum"] is True:
		if value > 0:
			color = {'r':1,'g':0,'b':0,'a':1}
		elif value > -0.2:
			color = {'r':0,'g':1,'b':0,'a':1}
		elif value > -0.5:
			color = {'r':(-value-0.2)/0.3,'g':1,'b':0,'a':1}
		else:
			f = min((-value-0.5)/0.5, 1)
			color = {'r':1,'g':1,'b':f,'a':1}
	else:
		if value > 0:
			color = {'r':1,'g':0,'b':0,'a':1}
		elif value > -0.2:
			color = {'r':0,'g':1,'b':0,'a':1}
		elif value > -0.5:
			color = {'r':1,'g':1,'b':0,'a':1}
		else:
			color = {'r':1,'g':1,'b':1,'a':1}

	return color


def sizeInputHandler(value):
	global Options, TextInputs
	try:
		Options["size"] = float(value)
		updateTextInputs()
		saveOptions()
	except ValueError:
		pass

def radScaleInputHandler(value):
	global Options, TextInputs
	try:
		Options["radScale"] = float(value)
		updateTextInputs()
		saveOptions()
	except ValueError:
		pass

def peakTimeInputHandler(value):
	global Options, TextInputs
	try:
		Options["peakTime"] = float(value)
		updateTextInputs()
		saveOptions()
	except ValueError:
		pass

def graphWidthInputHandler(value):
	global Options, TextInputs
	try:
		Options["graphWidth"] = int(value)
		updateTextInputs()
		saveOptions()
	except ValueError:
		pass

def graphHeightInputHandler(value):
	global Options, TextInputs
	try:
		Options["graphHeight"] = int(value)
		updateTextInputs()
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


def logscaleHandler(x, y):
	global Options, Buttons
	Options["logscale"] = not Options["logscale"]
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
	ac.setText(TextInputs["Flapper Size"], str(Options["size"]))
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
			Options = pickle.load(handle)
	except IOError:
		pass
