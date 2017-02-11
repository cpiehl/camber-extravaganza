##############################################################
# Camber Extravaganza!
# App for showing camber in real time
# Useful for tuning?
#
# TODO:
#   - Save options
#   - Text input for size, radscale, peaktime, etc
#   - Make log scale better
#
# Changelog:
#
# V1.0 - Initial version
#      - instant and peak values with flappers
#
# V1.1 - Graphs
#      - color spectrum instead of color steps
#      - self-normalizing graphs
#      - log scale graphs
#      - options menu
#############################################################

import ac
import acsys
import collections
import math

appWindow = 0
FLCamberIndicator = 0
FRCamberIndicator = 0
RLCamberIndicator = 0
RRCamberIndicator = 0
optionsCheckBox = 0
drawGraphsCheckBox = 0
normalizeCheckBox = 0
logscaleCheckBox = 0
spectrumCheckBox = 0
drawGraphs = False
logscale = False
normalize = False
useSpectrum = False
size = 50        # flapper length
radScale = 10    # flappiness ratio
peakTime = 2     # seconds
graphWidth = 150 # in pixels, also the number of frames of data to display
graphHeight = 60 # in pixels

class CamberIndicator:
	def __init__(self, app, x, y):
		self.xPosition = x
		self.yPosition = y
		self.value = 0
		self.peakValue = 0
		self.peakTime = 0
		self.color = {'r':1,'g':1,'b':1,'a':1}
		self.serie = collections.deque(maxlen=graphWidth)
		self.minVal = -4.5
		self.maxVal = 1.5
		self.minValLog1p = math.log1p(-self.minVal)
		self.maxValLog1p = math.log1p(self.maxVal)

		self.valueLabel = ac.addLabel(appWindow, "0.0°")
		ac.setPosition(self.valueLabel, x, y)
		self.peakValueLabel = ac.addLabel(appWindow, "0.0°")
		ac.setPosition(self.peakValueLabel, x, y + 18)


	def setValue(self, value, deltaT):
		global peakTime
		self.value = value
		deg = math.degrees(self.value)
		ac.setText(self.valueLabel,"{0:.3f}°".format(deg))

		self.serie.append(deg)

		self.color = getColor(deg)

		self.peakTime -= deltaT
		if self.peakTime <= 0:
			self.peakValue = value

		if value >= self.peakValue:
			self.peakTime = peakTime
			self.peakValue = value
			ac.setFontColor(self.peakValueLabel,
				self.color['r'],
				self.color['g'],
				self.color['b'],
				self.color['a']
			)
			ac.setText(self.peakValueLabel,"{0:.3f}°".format(math.degrees(self.peakValue)))


	def drawGauge(self, flip=False):
		global radScale, size
		ac.glColor4f(
			self.color['r'],
			self.color['g'],
			self.color['b'],
			self.color['a']
		)

		x = self.xPosition
		y = self.yPosition
		rad = self.value * radScale
		if flip:
			x += 50
			rad = math.pi - rad

		ac.glBegin(acsys.GL.Lines)
		ac.glVertex2f(x, y)
		ac.glVertex2f(x+size*math.cos(rad), y+size*math.sin(rad))
		ac.glEnd()


	def drawGraph(self, flip=False):
		global graphHeight, graphWidth, logscale, normalize
		x = self.xPosition
		y = self.yPosition + 5
		dx1 = 55
		dx2 = dx1 + graphWidth
		f = 1 # flip mult thisisreallydumbbutineedit
		if flip:
			dx1 = -5
			dx2 = dx1 - graphWidth
			f = -1

		halfHeight = graphHeight / 2
		middleHeight = graphHeight / 4
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
		if logscale:
			scaleNeg = -(halfHeight + middleHeight) / self.minValLog1p
			scalePos = (halfHeight - middleHeight) / self.maxValLog1p
		else:
			scaleNeg = -(halfHeight + middleHeight) / self.minVal
			scalePos = (halfHeight - middleHeight) / self.maxVal
		for i in range(len(self.serie)):
			color = getColor(self.serie[i])
			h = max(min(self.maxVal,self.serie[i]),self.minVal)
			if logscale:
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

		if normalize and len(self.serie) == graphWidth:
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
	global appWindow, FRCamberIndicator, FLCamberIndicator, RRCamberIndicator, RLCamberIndicator, optionsCheckBox, drawGraphsCheckBox, normalizeCheckBox, logscaleCheckBox, spectrumCheckBox
	appWindow = ac.newApp("CamberExtravaganza")
	ac.setSize(appWindow, 200, 200)
	ac.drawBorder(appWindow, 0)
	ac.setBackgroundOpacity(appWindow, 0)
	ac.setIconPosition(appWindow, 0, -10000)

	optionsCheckBox = ac.addCheckBox(appWindow, "Options")
	ac.setPosition(optionsCheckBox, 10, 200)
	ac.addOnCheckBoxChanged(optionsCheckBox, checkboxHandler)
	drawGraphsCheckBox = ac.addCheckBox(appWindow, "Draw Graphs")
	ac.setPosition(drawGraphsCheckBox, 10, 230)
	ac.addOnCheckBoxChanged(drawGraphsCheckBox, checkboxHandler)
	normalizeCheckBox = ac.addCheckBox(appWindow, "Normalize")
	ac.setPosition(normalizeCheckBox, 10, 260)
	ac.addOnCheckBoxChanged(normalizeCheckBox, checkboxHandler)
	logscaleCheckBox = ac.addCheckBox(appWindow, "Log Scale")
	ac.setPosition(logscaleCheckBox, 10, 290)
	ac.addOnCheckBoxChanged(logscaleCheckBox, checkboxHandler)
	spectrumCheckBox = ac.addCheckBox(appWindow, "Use Spectrum")
	ac.setPosition(spectrumCheckBox, 160, 230)
	ac.addOnCheckBoxChanged(spectrumCheckBox, checkboxHandler)

	ac.setVisible(drawGraphsCheckBox, 0)
	ac.setVisible(normalizeCheckBox, 0)
	ac.setVisible(logscaleCheckBox, 0)
	ac.setVisible(spectrumCheckBox, 0)

	FLCamberIndicator = CamberIndicator(appWindow, 25, 50)
	FRCamberIndicator = CamberIndicator(appWindow,125, 50)
	RLCamberIndicator = CamberIndicator(appWindow, 25,150)
	RRCamberIndicator = CamberIndicator(appWindow,125,150)
	ac.addRenderCallback(appWindow, onFormRender)
	return "CamberExtravaganza"


def onFormRender(deltaT):
	global scale, FRCamberIndicator, FLCamberIndicator, RRCamberIndicator, RLCamberIndicator
	# Draw flappy gauges
	FLCamberIndicator.drawGauge(flip=True)
	FRCamberIndicator.drawGauge()
	RLCamberIndicator.drawGauge(flip=True)
	RRCamberIndicator.drawGauge()
	# Draw history graphs
	if drawGraphs:
		FLCamberIndicator.drawGraph(flip=True)
		FRCamberIndicator.drawGraph()
		RLCamberIndicator.drawGraph(flip=True)
		RRCamberIndicator.drawGraph()
	w,x,y,z = ac.getCarState(0, acsys.CS.CamberRad)
	FLCamberIndicator.setValue(w, deltaT)
	FRCamberIndicator.setValue(x, deltaT)
	RLCamberIndicator.setValue(y, deltaT)
	RRCamberIndicator.setValue(z, deltaT)


def getColor(value):
	global useSpectrum
	color = {}
	if useSpectrum is True:
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


def checkboxHandler(name, value):
	global drawGraphs, normalize, logscale, useSpectrum, drawGraphsCheckBox, normalizeCheckBox, logscaleCheckBox, spectrumCheckBox
	if name == "Options":
		visible = 1 if value == 1 else 0
		ac.setVisible(drawGraphsCheckBox, visible)
		ac.setVisible(normalizeCheckBox, visible)
		ac.setVisible(logscaleCheckBox, visible)
		ac.setVisible(spectrumCheckBox, visible)
	elif name == "Draw Graphs":
		if value == 1:
			drawGraphs = True
		else:
			drawGraphs = False
	elif name == "Normalize":
		if value == 1:
			normalize = True
		else:
			normalize = False
	elif name == "Log Scale":
		if value == 1:
			logscale = True
		else:
			logscale = False
	elif name == "Use Spectrum":
		if value == 1:
			useSpectrum = True
		else:
			useSpectrum = False
