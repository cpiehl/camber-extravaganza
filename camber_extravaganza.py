##############################################################
# Camber Extravaganza!
# App for showing camber in real time
# Useful for tuning?
#############################################################

import ac
import acsys
import math

appWindow = 0
FLCamberIndicator = 0
FRCamberIndicator = 0
RLCamberIndicator = 0
RRCamberIndicator = 0
size = 50
radScale = 10
peakTime = 1.5 # seconds

class CamberIndicator:
	def __init__(self, app, x, y):
		self.xPosition = x
		self.yPosition = y
		self.value = 0
		self.peakValue = 0
		self.peakTime = 0
		self.color = {'r':1,'g':1,'b':1,'a':1}

		self.valueLabel = ac.addLabel(appWindow, "0.0°")
		ac.setPosition(self.valueLabel, x, y)
		self.peakValueLabel = ac.addLabel(appWindow, "0.0°")
		ac.setPosition(self.peakValueLabel, x, y + 18)


	def setValue(self, value, deltaT):
		global peakTime
		self.value = value
		ac.setText(self.valueLabel,"{0:.3f}°".format(math.degrees(self.value)))

		if self.value > 0:
			self.color = {'r':1,'g':0,'b':0,'a':1}
		elif self.value > -0.01:
			self.color = {'r':1,'g':0.5,'b':0,'a':1}
		else:
			self.color = {'r':1,'g':1,'b':1,'a':1}

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


# This function gets called by AC when the Plugin is initialised
# The function has to return a string with the plugin name
def acMain(ac_version):
	global appWindow, FRCamberIndicator, FLCamberIndicator, RRCamberIndicator, RLCamberIndicator
	appWindow = ac.newApp("CamberExtravaganza")
	ac.setSize(appWindow, 200, 200)
	ac.drawBorder(appWindow, 0)
	ac.setBackgroundOpacity(appWindow, 0)
	ac.setIconPosition(appWindow, 0, -10000)
	FLCamberIndicator = CamberIndicator(appWindow, 25, 50)
	FRCamberIndicator = CamberIndicator(appWindow,125, 50)
	RLCamberIndicator = CamberIndicator(appWindow, 25,150)
	RRCamberIndicator = CamberIndicator(appWindow,125,150)
	ac.addRenderCallback(appWindow, onFormRender)
	return "CamberExtravaganza"


def onFormRender(deltaT):
	global scale, FRCamberIndicator, FLCamberIndicator, RRCamberIndicator, RLCamberIndicator
	FLCamberIndicator.drawGauge(flip=True)
	FRCamberIndicator.drawGauge()
	RLCamberIndicator.drawGauge(flip=True)
	RRCamberIndicator.drawGauge()
	w,x,y,z = ac.getCarState(0, acsys.CS.CamberRad)
	FLCamberIndicator.setValue(w, deltaT)
	FRCamberIndicator.setValue(x, deltaT)
	RLCamberIndicator.setValue(y, deltaT)
	RRCamberIndicator.setValue(z, deltaT)
