#
#  Partnerbox E2
#
#  $Id$
#
#  Coded by Dr.Best (c) 2009
#  Support: board.dreambox-tools.info
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#

from Plugins.Plugin import PluginDescriptor
from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Screens.InputBox import PinInput
from Screens.TimerEdit import TimerEditList
from Components.TimerList import TimerList
from Components.config import config
from Components.ScrollLabel import ScrollLabel
from Components.ActionMap import ActionMap, NumberActionMap
from Components.MenuList import MenuList
from Components.Label import Label
from Components.Button import Button
from Components.EpgList import Rect
from Components.MultiContent import MultiContentEntryText
from Components.Pixmap import Pixmap
from enigma import eServiceReference
from enigma import eListboxPythonMultiContent, eListbox, gFont, \
	RT_HALIGN_LEFT, RT_HALIGN_RIGHT, RT_VALIGN_CENTER
from Tools.LoadPixmap import LoadPixmap
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.FuzzyDate import FuzzyTime
from Tools.BoundFunction import boundFunction
from timer import TimerEntry
from enigma import eTimer
from time import localtime
import time
import xml.etree.cElementTree
import urllib
from Screens.InfoBarGenerics import InfoBarAudioSelection
from RemoteTimerEntry import RemoteTimerEntry, RemoteTimerInit
from PartnerboxEPGSelection import Partnerbox_EPGSelectionInit

from PartnerboxFunctions import E2Timer, FillE2TimerList, sendPartnerBoxWebCommand, isInTimerList

from PartnerboxEPGList import Partnerbox_EPGListInit
from PartnerboxSetup import PartnerboxSetup, PartnerboxEntriesListConfigScreen, initConfig

from Services import Services, E2EPGListAllData, E2ServiceList
from Screens.ChannelSelection import service_types_tv
from Screens.Standby import TryQuitMainloop

from Components.config import ConfigSubsection, ConfigSubList, ConfigInteger, ConfigYesNo

from Components.GUIComponent import GUIComponent
from skin import TemplatedListFonts, componentSizes
from timer import TimerEntry as RealTimerEntry

from ServiceReference import ServiceReference

config.plugins.Partnerbox = ConfigSubsection()
config.plugins.Partnerbox.showremotetimerinextensionsmenu= ConfigYesNo(default = True)
config.plugins.Partnerbox.showremotetimerinmainmenu = ConfigYesNo(default = False)
config.plugins.Partnerbox.enablepartnerboxintimerevent = ConfigYesNo(default = False)
config.plugins.Partnerbox.enablepartnerboxepglist = ConfigYesNo(default = False)
config.plugins.Partnerbox.enabledefaultpartnerboxintimeredit = ConfigYesNo(default = False)
config.plugins.Partnerbox.entriescount =  ConfigInteger(0)
config.plugins.Partnerbox.Entries = ConfigSubList()
initConfig()

def showPartnerboxIconsinEPGList():
	# for epgsearch	
	return config.plugins.Partnerbox.enablepartnerboxepglist.value

def partnerboxpluginStart(session, what):
	count = config.plugins.Partnerbox.entriescount.value
	if count == 1:
		partnerboxplugin(session, what, config.plugins.Partnerbox.Entries[0])
	else:
		session.openWithCallback(partnerboxplugin, PartnerboxEntriesListConfigScreen, what)

def partnerboxplugin(session, what, partnerboxentry = None):
	if partnerboxentry is None:
		return
	if what == 2: # RemoteTimer
		session.open(RemoteTimerList, partnerboxentry)

def autostart_RemoteTimerInit(reason, **kwargs):
	if "session" in kwargs:
		session = kwargs["session"]
		try: RemoteTimerInit()
		except: pass

def autostart_Partnerbox_EPGList(reason, **kwargs):
	if "session" in kwargs:
		session = kwargs["session"]
		try: 
			Partnerbox_EPGListInit()
			Partnerbox_EPGSelectionInit()
		except: pass

def PartnerboxSetupFinished(session, result):
	if result:
		session.openWithCallback(boundFunction(restartGUI, session), MessageBox,_("You have to restart Enigma2 to activate your new preferences! Restart now?"), MessageBox.TYPE_YESNO)
		
def restartGUI(session, answer):
	if answer:
		session.open(TryQuitMainloop, 3)

def setup(session,**kwargs):
	session.openWithCallback(PartnerboxSetupFinished, PartnerboxSetup)

def main(session,**kwargs):
	partnerboxpluginStart(session, 2)
	
def mainmenu(menuid, **kwargs):
	if menuid == "mainmenu":
		return [(_("Partnerbox: RemoteTimer"), main, "remotetimer", 43)]
	return []

def Plugins(**kwargs):
	list = [PluginDescriptor(name="Partnerbox: RemoteTimer", description=_("Manage timer for other dreamboxes in network"), 
		where = [PluginDescriptor.WHERE_EVENTINFO ], fnc=main)]
	if config.plugins.Partnerbox.enablepartnerboxintimerevent.value:
		list.append(PluginDescriptor(where = PluginDescriptor.WHERE_SESSIONSTART, fnc = autostart_RemoteTimerInit))
	if config.plugins.Partnerbox.enablepartnerboxepglist.value:
		list.append(PluginDescriptor(where = PluginDescriptor.WHERE_SESSIONSTART, fnc = autostart_Partnerbox_EPGList))
	list.append(PluginDescriptor(where = PluginDescriptor.WHERE_SESSIONSTART, fnc = autostart_ChannelContextMenu))
	list.append(PluginDescriptor(name="Setup Partnerbox", description=_("setup for partnerbox"), where = [PluginDescriptor.WHERE_PLUGINMENU], icon = "Setup_Partnerbox.png", fnc=setup))
	if config.plugins.Partnerbox.showremotetimerinextensionsmenu.value:
		list.append(PluginDescriptor(name="Partnerbox: RemoteTimer", description=_("Manage timer for other dreamboxes in network"), 
		where = [PluginDescriptor.WHERE_EXTENSIONSMENU], fnc=main))
	if config.plugins.Partnerbox.showremotetimerinmainmenu.value:
		list.append(PluginDescriptor(name="Partnerbox: RemoteTimer", description=_("Manage timer for other dreamboxes in network"),
		where = [PluginDescriptor.WHERE_MENU], fnc=mainmenu))
	
	return list
			
def FillLocationList(xmlstring):
	Locations = []
	try: root = xml.etree.cElementTree.fromstring(xmlstring)
	except: Locations 
	for location in root.findall("e2location"):
		Locations.append(location.text.encode("utf-8", 'ignore'))
	for location in root.findall("e2simplexmlitem"):  # vorerst Kompatibilitaet zum alten Webinterface-Api aufrecht erhalten (e2simplexmlitem)
		Locations.append(location.text.encode("utf-8", 'ignore'))
	return Locations
		
class RemoteTimerList(TimerEditList):
	skin = """  <screen name="RemoteTimerList" position="center,120" size="950,520" title="Remote Timer Editor">
    	<ePixmap pixmap="skin_default/buttons/red.png" position="10,5" size="200,40" alphatest="on" />
	    <ePixmap pixmap="skin_default/buttons/green.png" position="210,5" size="200,40" alphatest="on" />
    	<ePixmap pixmap="skin_default/buttons/yellow.png" position="410,5" size="200,40" alphatest="on" />
	    <ePixmap pixmap="skin_default/buttons/blue.png" position="610,5" size="200,40" alphatest="on" />
	    <widget name="menubutton" pixmap="skin_default/icons/menu.png" position="810,15" size="100,20" alphatest="on" />
	    <widget name="key_red" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
	    <widget name="key_green" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
	    <widget name="key_yellow" position="410,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
	    <widget name="key_blue" position="610,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
	    <eLabel position="10,50" size="930,1" backgroundColor="grey" />
    	<widget name="timerlist" position="10,60" size="930,450" enableWrapAround="1" scrollbarMode="showOnDemand" />
	  </screen> """
	def __init__(self, session, partnerboxentry = None):
		self.skinName = "RemoteTimerList"
		self.partnerboxentry = partnerboxentry
		self["RemoteTimerActions"] = ActionMap(["MenuActions"],
		{
			"menu": self.changePartnerbox,
		}, -1)
		
		self["menubutton"] = Pixmap()
		self.count = config.plugins.Partnerbox.entriescount.value
		if self.count == 1:
			self["menubutton"].hide()
		
		TimerEditList.__init__(self, session)
		self["timerlist"] = TimerList(list)
		self["timerlist"].l.setBuildFunc(self.buildRemoteTimerEntry)
		self.onLayoutFinish.append(self.readRemoteTimers)
		
	def changePartnerbox(self):
		if self.count > 1:
			self.session.openWithCallback(self.openNewPartnerbox, PartnerboxEntriesListConfigScreen)
		
	def openNewPartnerbox(self, session, what, partnerboxentry):
		if partnerboxentry is not None:
			self.partnerboxentry = partnerboxentry
			self.readRemoteTimers()
		
	def buildRemoteTimerEntry(self, timer, processed):
		pixmap = None
		s_ref = ServiceReference(timer.servicereference)
		if s_ref.ref.flags & eServiceReference.isGroup:
			pixmap = self.picServiceGroup
		else:
			orbpos = s_ref.ref.getUnsignedData(4) >> 16
			if orbpos == 0xFFFF:
				pixmap = self["timerlist"].picDVB_C
			elif orbpos == 0xEEEE:
				pixmap = self["timerlist"].picDVB_T
			else:
				pixmap = self["timerlist"].picDVB_S

		res = [ None ]
		
		res.append(timer.servicename)
		res.append(pixmap)
		res.append(timer.name)
		
		repeatedtext = ""
		days = ( _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") )

		if timer.repeated:
			flags = timer.repeated
			count = 0
			for x in (0, 1, 2, 3, 4, 5, 6):
					if (flags & 1 == 1):
						if (count != 0):
							repeatedtext += ", "
						repeatedtext += days[x]
						count += 1
					flags = flags >> 1
			if timer.justplay:
				if timer.timeend - timer.timebegin < 4: # rounding differences
					repeatedtext += ((" %s "+ _("(ZAP)")) % (FuzzyTime(timer.timebegin)[1]))
				else:
					repeatedtext += ((" %s ... %s (%d " + _("mins") + ") ") % (FuzzyTime(timer.timebegin)[1], FuzzyTime(timer.timeend)[1], (timer.timeend - timer.timebegin) / 60)) + _("(ZAP)")
			else:
				repeatedtext += ((" %s ... %s (%d " + _("mins") + ")") % (FuzzyTime(timer.timebegin)[1], FuzzyTime(timer.timeend)[1], (timer.timeend - timer.timebegin) / 60))
		else:
			if timer.justplay:
				if timer.timeend - timer.timebegin < 4:
					repeatedtext += (("%s, %s " + _("(ZAP)")) % (FuzzyTime(timer.timebegin)))
				else:
					repeatedtext += (("%s, %s ... %s (%d " + _("mins") + ") ") % (FuzzyTime(timer.timebegin) + FuzzyTime(timer.timeend)[1:] + ((timer.timeend - timer.timebegin) / 60,))) + _("(ZAP)")
			else:
				repeatedtext += (("%s, %s ... %s (%d " + _("mins") + ")") % (FuzzyTime(timer.timebegin) + FuzzyTime(timer.timeend)[1:] + ((timer.timeend - timer.timebegin) / 60,)))

		res.append(repeatedtext)

		if not processed:
			if timer.state == TimerEntry.StateWaiting:
				state = _("waiting")
			elif timer.state == TimerEntry.StatePrepared:
				state = _("about to start")
			elif timer.state == TimerEntry.StateRunning:
				if timer.justplay:
					state = _("zapped")
				else:
					state = _("recording...")
			elif timer.state == TimerEntry.StateEnded:
				state = _("done!")
			else:
				state = _("<unknown>")
		else:
			state = _("done!")

		if timer.disabled:
			state = _("disabled")
		res.append(state)
		png = None
		if timer.disabled:
			png = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, "skin_default/icons/redx.png"))

		res.append(png)
		
		return res		
	
	def readRemoteTimers(self):
		self.ip = "%d.%d.%d.%d" % tuple(self.partnerboxentry.ip.value)
		self.port = self.partnerboxentry.port.value
		self.username = "root"
		self.password = self.partnerboxentry.password.value
		self.webiftype = self.partnerboxentry.webinterfacetype.value		

		self.setTitle("Remote Timer Editor %s" %(self.partnerboxentry.name.value))	

		self.count = config.plugins.Partnerbox.entriescount.value
		if self.count == 1:
			self["menubutton"].hide()
		
		self["timerlist"].hide()
		
		sCommand = "http://%s:%d/web/timerlist" % (self.ip,self.port)

		sendPartnerBoxWebCommand(sCommand, 10, self.username, self.password, self.webiftype).addCallback(self.downloadCallback).addErrback(self.downloadError)
		
	def downloadCallback(self, callback = None):
		self.readXML(callback)
		self["timerlist"].instance.show()

	def downloadError(self, error = None):
		if error is not None:
			self.session.open(MessageBox,str(error.getErrorMessage()),  MessageBox.TYPE_INFO)
			
	def readXML(self, xmlstring):
		self.E2TimerList = []
		self.E2TimerList = FillE2TimerList(xmlstring)

		#helper function to move finished timers to end of list
		def eol_compare(x, y):
			if x[0].state != y[0].state and x[0].state == RealTimerEntry.StateEnded or y[0].state == RealTimerEntry.StateEnded:
				return cmp(x[0].state, y[0].state)
			return cmp(x[0].begin, y[0].begin)
		
		list = self.list
		del list[:]
		list.extend([(x,True) for x in self.E2TimerList if x.state == 3])
		list.extend([(x,False) for x in self.E2TimerList if x.state < 3])
		if config.usage.timerlist_finished_timer_position.index: #end of list
			list.sort(cmp = eol_compare)
		else:
			list.sort(key = lambda x: x[0].begin)		
		
		self["timerlist"].l.setList(list)
		self.updateState()
		
	def toggleDisabledState(self):
		t =  self["timerlist"].getCurrent()
		
		if t.disabled == 0:
			disabled = 1
		else:
			disabled = 0
		
		#sCommand = "http://%s:%d/web/timerchange?sRef=%s&begin=%s&end=%s&name=%s&description=%s&dirname=%s&tags=&afterevent=%s&eit=%s&disabled=%s&justplay=%s&channelOld=%s&beginOld=%s&endOld=%s&deleteOldOnSave=1" % (self.ip, self.port, t.servicereference, t.timebegin, t.timeend, urllib.quote(t.name), urllib.quote(t.description), urllib.quote(t.dirname), t.afterEvent, t.eventId, disabled, t.justplay, t.servicereference, t.timebegin, t.timeend  )
		sCommand = "http://%s:%d/web/timerchange?sRef=%s&begin=%s&end=%s&name=%s&description=%s&dirname=%s&tags=&afterevent=%s&eit=%s&disabled=%s&justplay=%s&channelOld=%s&beginOld=%s&endOld=%s&deleteOldOnSave=1" % (self.ip, self.port, t.servicereference, t.timebegin, t.timeend, urllib.quote(t.name), urllib.quote(t.description), urllib.quote(t.dirname), t.afterEvent, t.eit, disabled, t.justplay, t.servicereference, t.timebegin, t.timeend  )
		
		sendPartnerBoxWebCommand(sCommand, 10, self.username, self.password, self.webiftype).addCallback(self.timerChangeCallback).addErrback(self.actionError)
		
	def timerChangeCallback(self, result):
		self.readRemoteTimers()
		
	def actionError(self, error):
		self.session.open(MessageBox,str(error.getErrorMessage()),  MessageBox.TYPE_INFO)
		
	def removeTimerQuestion(self):
		t = self["timerlist"].getCurrent()
		if not t:
			return
		
		self.session.openWithCallback(self.removeTimer, MessageBox, _("Do you really want to delete %s?") %(t.name))
		
	def removeTimer(self, result):
		if not result:
			return
		
		t = self["timerlist"].getCurrent()
		if t:
			sCommand = "http://%s:%d/web/timerdelete?sRef=%s&begin=%s&end=%s" %(self.ip, self.port, t.servicereference, t.timebegin, t.timeend)
			
			sendPartnerBoxWebCommand(sCommand, 10, self.username, self.password, self.webiftype).addCallback(self.timerDeleteCallback).addErrback(self.actionError)
			
	def timerDeleteCallback(self, result):
		self.readRemoteTimers()

	def addTimer(self, timer):
		from RemoteTimerEntry import RemoteTimerEntry
		self.session.openWithCallback(self.finishedAdd, RemoteTimerEntry, timer, [], self.partnerboxentry, self.E2TimerList)	
	
	def finishedAdd(self, answer):
		if answer[0]:
			pass
		else:
			print "Timeredit aborted"
		self.readRemoteTimers()

	def openEdit(self):
		self.currentTimer=self["timerlist"].getCurrent()
		if self.currentTimer:
			from RemoteTimerEntry import getLocations
			self.timeBeginOld = self.currentTimer.timebegin
			self.timeEndOld = self.currentTimer.timeend
			self.srefOld = self.currentTimer.servicereference
			
			self.Locations = []
	
			ip = "%d.%d.%d.%d" % tuple(self.partnerboxentry.ip.value)
			port = self.partnerboxentry.port.value
			http_ = "%s:%d" % (ip,port)
			getLocations(self, "http://" + http_ + "/web/getlocations", self.partnerboxentry, False, "edit")
		
	def	openEditCallback(self):
		#self.session.openWithCallback(self.finishedEdit, RemoteTimerEntry, self.currentTimer, self.Locations, self.partnerboxentry)
		self.session.openWithCallback(self.finishedEdit, RemoteTimerEntry, self.currentTimer, self.Locations, self.partnerboxentry, self.E2TimerList)
	
	def finishedEdit(self, answer):
		if answer[0]:
			t = answer[1]
			#sCommand = "http://%s:%d/web/timerchange?sRef=%s&begin=%s&end=%s&name=%s&description=%s&dirname=%s&tags=&afterevent=%s&eit=%s&disabled=%s&justplay=%s&channelOld=%s&beginOld=%s&endOld=%s&deleteOldOnSave=1" % (self.ip, self.port, t.servicereference, t.timebegin, t.timeend, urllib.quote(t.name), urllib.quote(t.description), urllib.quote(t.dirname), t.afterEvent, t.eventId, t.disabled, t.justplay, self.srefOld, self.timeBeginOld, self.timeEndOld   )
			sCommand = "http://%s:%d/web/timerchange?sRef=%s&begin=%s&end=%s&name=%s&description=%s&dirname=%s&tags=&afterevent=%s&eit=%s&disabled=%s&justplay=%s&channelOld=%s&beginOld=%s&endOld=%s&deleteOldOnSave=1" % (self.ip, self.port, t.servicereference, t.timebegin, t.timeend, urllib.quote(t.name), urllib.quote(t.description), urllib.quote(t.dirname), t.afterEvent, t.eit, t.disabled, t.justplay, self.srefOld, self.timeBeginOld, self.timeEndOld   )			
		
			sendPartnerBoxWebCommand(sCommand, 10, self.username, self.password, self.webiftype).addCallback(self.timerChangeCallback).addErrback(self.actionError)
		else:
			print "Timeredit aborted"
	
	def cleanupTimer(self, delete):
		if delete:
			sCommand = "http://%s:%d/web/timercleanup?cleanup=true" % (self.ip, self.port)
			
			sendPartnerBoxWebCommand(sCommand, 10, self.username, self.password, self.webiftype).addCallback(self.timerChangeCallback).addErrback(self.actionError)
			
	def cleanupTimerCallback(self, result):
		self.readRemoteTimers()

class RemoteTimerEPGList(Screen):
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2
	skin = """
		<screen name="RemoteTimerEPGList" position="center,120" size="950,520" title ="EPG Selection">
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="210,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="410,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="610,5" size="200,40" alphatest="on" />
			<widget name="key_red" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_green" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_yellow" position="410,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_blue" position="610,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<eLabel position="10,50" size="930,1" backgroundColor="grey" />
			<widget name="epglist" position="10,60" size="930,450" zPosition="2" enableWrapAround="1" scrollbarMode="showOnDemand" />
			<widget name="text" position="10,60" size="930,450" zPosition="1" font="Regular;20" halign="center" valign="center" />
		</screen>"""
	
	def __init__(self, session, E2Timerlist, ServiceReference, ServiceName, partnerboxentry, showAddTimer = True):
		self.session = session
		self.showAddTimer = showAddTimer
		Screen.__init__(self, session)
		self.E2TimerList = E2Timerlist
		self["epglist"] = E2EPGList([],selChangedCB = self.onSelectionChanged)
		self["key_red"] = Label()# Dummy, kommt eventuell noch was
		if showAddTimer:
			self["key_green"] = Label(_("Add timer"))
		else:
			self["key_green"] = Label(_("Apply"))
		self.key_green_choice = self.ADD_TIMER
		self["key_yellow"] = Label() # Dummy, kommt eventuell noch was
		self["key_blue"] = Label(_("Info"))
		self["text"] = Label(_("Getting EPG Information..."))
		self.onLayoutFinish.append(self.startRun)
		self.servicereference = ServiceReference
		self["actions"] = ActionMap(["WizardActions", "DirectionActions", "ColorActions"],
		{
			"back": self.closeScreen,
			"green": self.GreenPressed,
			"blue": self.EPGEvent,
		}, -1)
		
		self.PartnerboxEntry = partnerboxentry
		self.password = partnerboxentry.password.value
		self.username = "root"
		try:
			self.webiftype = partnerboxentry.webinterfacetype.value
		except:
			self.webiftype = "standard"
		self.ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
		port = partnerboxentry.port.value
		self.http = "http://%s:%d" % (self.ip,port)
		self.useinternal = int(partnerboxentry.useinternal.value)
		
		self.url = self.http + "/web/epgservice?sRef=" + urllib.quote(self.servicereference.decode('utf8').encode('latin-1','ignore'))
		self.ListCurrentIndex = 0
		self.Locations = []

	def closeScreen(self):
		if self.showAddTimer:
			self.close()
		else:
			self.close([])
		
	def EPGEvent(self):
		
		sel = self["epglist"].l.getCurrentSelection()[0]
		if sel is None:
			return
		self.session.openWithCallback(self.CallbackEPGEvent, RemoteTimerEventView, self.E2TimerList, sel, self.PartnerboxEntry)
		
	def CallbackEPGEvent(self):
		pass
		
	def onSelectionChanged(self):
		cur = self["epglist"].getCurrent()
		if cur is None:
			self["key_green"].setText("")
			self.key_green_choice = self.EMPTY
			self["key_blue"].setText("")
			return
		serviceref = cur[0].servicereference
		eventid = cur[0].eventid
		if eventid ==0:
			self["key_green"].setText("")
			self.key_green_choice = self.EMPTY
			self["key_blue"].setText("")
			return
		self["key_blue"].setText(_("Info"))
		
		timerentry = isInTimerList(cur[0].eventstart,cur[0].eventduration, cur[0].servicereference, cur[0].eventid, self.E2TimerList)
		if timerentry is None:
			if self.key_green_choice != self.ADD_TIMER:
				self["key_green"].setText(_("Add timer"))
				self.key_green_choice = self.ADD_TIMER
		else:
			if self.key_green_choice != self.REMOVE_TIMER:
				self["key_green"].setText(_("Remove timer"))
				self.key_green_choice = self.REMOVE_TIMER
	
	def startRun(self):
		if self.useinternal == 1:
			EPGList = []
			a = Services(self.session)
			EPGList = a.buildEPGList(self.servicereference)
			self["epglist"].buildList(EPGList, self.E2TimerList)
			if self.ListCurrentIndex != 0:
				sel = self["epglist"].moveSelectionTo(self.ListCurrentIndex)
				self.ListCurrentIndex = 0
		else:
			self["epglist"].instance.hide()
			self.getEPGList()
	
	def getEPGList(self):
			sendPartnerBoxWebCommand(self.url, 10, self.username, self.password, self.webiftype).addCallback(self.EPGListDownloadCallback).addErrback(self.EPGListDownloadError)
		
	def EPGListDownloadCallback(self, callback = None):
		self.readXMLEPGList(callback)
		self["epglist"].instance.show()
	
	def EPGListDownloadError(self, error = None):
		if error is not None:
			self["text"].setText(str(error.getErrorMessage()))
	
	def readXMLEPGList(self, xmlstring):
		E2ListEPG = []
		root = xml.etree.cElementTree.fromstring(xmlstring)
		for events in root.findall("e2event"):
			servicereference = str(events.findtext("e2eventservicereference", '').encode("utf-8", 'ignore'))
			servicename = str(events.findtext("e2eventservicename", 'n/a').encode("utf-8", 'ignore'))
			try:eventstart = int(events.findtext("e2eventstart", 0))
			except:eventstart = 0
			try:eventduration = int(events.findtext("e2eventduration", 0))
			except:eventduration  = 0
			try:eventtitle = str(events.findtext("e2eventtitle", '').encode("utf-8", 'ignore'))
			except:eventtitle = ""
			try:eventid = int(events.findtext("e2eventid", 0))
			except:eventid = 0
			try:eventdescription = str(events.findtext("e2eventdescription", '').encode("utf-8", 'ignore'))
			except:eventdescription = ""
			try:eventdescriptionextended = str(events.findtext("e2eventdescriptionextended", '').encode("utf-8", 'ignore'))
			except:eventdescriptionextended = ""
			E2ListEPG.append(E2EPGListAllData(servicereference = servicereference, servicename = servicename, eventid = eventid, eventstart = eventstart, eventduration = eventduration, eventtitle = eventtitle, eventdescription = eventdescription, eventdescriptionextended = eventdescriptionextended  ))
		self["epglist"].buildList(E2ListEPG, self.E2TimerList)
		if self.ListCurrentIndex != 0:
			sel = self["epglist"].moveSelectionTo(self.ListCurrentIndex)
			self.ListCurrentIndex = 0
		
	def GreenPressed(self):
		if self.showAddTimer:
			if self.key_green_choice == self.ADD_TIMER:
				self.getLocations()
			elif self.key_green_choice == self.REMOVE_TIMER:
				self.deleteTimer()
		else:
			cur = self["epglist"].getCurrent()
			if cur is None:
				self.close(None)
			else:
				self.close([cur[0]])
	
	def LocationsError(self, error = None):
		if error is not None:
			self["epglist"].instance.hide()
			self["text"].setText(str(error.getErrorMessage()))
	
	def getLocations(self):
		sCommand = self.http + "/web/getlocations"
		sendPartnerBoxWebCommand(sCommand, 3, self.username, self.password, self.webiftype).addCallback(self.getLocationsCallback).addErrback(self.LocationsError)
	
	def getLocationsCallback(self, xmlstring):
		self.Locations = []
		self.Locations = FillLocationList(xmlstring)
		self.addTimerEvent()
			
	def addTimerEvent(self):
		cur = self["epglist"].getCurrent()
		if cur is None:
			return
		description = cur[0].eventdescription
		dirname = "/media/hdd/movie/"
		#timerentry = E2Timer(servicereference = cur[0].servicereference, servicename = cur[0].servicename, name = cur[0].eventtitle, disabled = 0, timebegin = cur[0].eventstart, timeend = cur[0].eventstart + cur[0].eventduration, duration = cur[0].eventduration, startprepare = 0, state = 0 , repeated = 0, justplay= 0, eventId = 0, afterevent = 0, dirname = dirname, description = description)
		timerentry = E2Timer(servicereference = cur[0].servicereference, servicename = cur[0].servicename, name = cur[0].eventtitle, disabled = 0, timebegin = cur[0].eventstart, timeend = cur[0].eventstart + cur[0].eventduration, duration = cur[0].eventduration, startprepare = 0, state = 0 , repeated = 0, justplay= 0, eit = 0, afterevent = 0, dirname = dirname, description = description)
		
		self.session.openWithCallback(self.RemoteTimerEntryFinished, RemoteTimerEntry,timerentry, self.Locations)

	def RemoteTimerEntryFinished(self, answer):
		if answer[0]:
			self.ListCurrentIndex = self["epglist"].getCurrentIndex()
			entry = answer[1]
			self["epglist"].instance.hide()
			ref = urllib.quote(entry.servicereference.decode('utf8').encode('latin-1','ignore')) + "&begin=" + ("%s"%(entry.timebegin)) + "&end=" + ("%s"%(entry.timeend))  + "&name=" + urllib.quote(entry.name) + "&description=" + urllib.quote(entry.description) + "&dirname=" + urllib.quote(entry.dirname) + "&eit=0&justplay=" + ("%s"%(entry.justplay)) + "&afterevent=" + ("%s"%(entry.afterevent))
			
			sCommand = self.http + "/web/timeradd?sRef=" + ref
			sendPartnerBoxWebCommand(sCommand, 10, self.username, self.password, self.webiftype).addCallback(self.deleteTimerCallback).addErrback(self.EPGListDownloadError)
	
	def deleteTimer(self):
		cur = self["epglist"].getCurrent()
		if cur is None:
			return
		#timerentry = isInTimerList(cur[0].eventstart,cur[0].eventduration, cur[0].servicereference, cur[0].eventid, self.E2TimerList)
		timerentry = isInTimerList(cur[0].eventstart,cur[0].eventduration, cur[0].servicereference, cur[0].eit, self.E2TimerList)
		if timerentry is None:
			return
		else:
			self.session.openWithCallback(self.deleteTimerConfirmed, MessageBox, _("Do you really want to delete the timer \n%s ?") % timerentry.name)

	def deleteTimerConfirmed(self, val):
		if val:
			cur = self["epglist"].getCurrent()
			if cur is None:
				return
			self.ListCurrentIndex = self["epglist"].getCurrentIndex()
			#timerentry = isInTimerList(cur[0].eventstart,cur[0].eventduration, cur[0].servicereference, cur[0].eventid, self.E2TimerList)
			timerentry = isInTimerList(cur[0].eventstart,cur[0].eventduration, cur[0].servicereference, cur[0].eit, self.E2TimerList)
			if timerentry is None:
				return
			else:
				self["epglist"].instance.hide()
				sCommand = self.http + "/web/timerdelete?sRef=" + timerentry.servicereference + "&begin=" + ("%s"%(timerentry.timebegin)) + "&end=" +("%s"%(timerentry.timeend))
				sendPartnerBoxWebCommand(sCommand, 3, self.username, self.password, self.webiftype).addCallback(self.deleteTimerCallback).addErrback(self.EPGListDownloadError)
	
	def deleteTimerCallback(self, callback = None):
		url = self.http + "/web/timerlist"
		sendPartnerBoxWebCommand(url, 10, self.username, self.password, self.webiftype).addCallback(self.readXML).addErrback(self.EPGListDownloadError)

	def readXML(self, xmlstring = None):
		if xmlstring is not None:
			self["text"].setText("Getting timerlist data...")
			self.E2TimerList = []
			self.E2TimerList = FillE2TimerList(xmlstring)
			self["text"].setText("Getting EPG data...")
			if self.useinternal == 1:
				EPGList = []
				a = Services(self.session)
				EPGList = a.buildEPGList(self.servicereference)
				self["epglist"].buildList(EPGList, self.E2TimerList)
				self["epglist"].instance.show()
				if self.ListCurrentIndex != 0:
					sel = self["epglist"].moveSelectionTo(self.ListCurrentIndex)
					self.ListCurrentIndex = 0
			else:
				self.getEPGList()

class E2BouquetList(MenuList):
	SKIN_COMPONENT_KEY = "PartnerboxList"
	SKIN_COMPONENT_LISTSMALL_HEIGHT = "listsmallHeight"
	SKIN_COMPONENT_SERVICENAME_HEIGHT = "servicenameHeight"	
	
	def __init__(self, list, enableWrapAround = True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		tlf = TemplatedListFonts()
		self.l.setFont(0, gFont(tlf.face(tlf.MEDIUM), tlf.size(tlf.MEDIUM)))
	def postWidgetCreate(self, instance):
		MenuList.postWidgetCreate(self, instance)
		sizes = componentSizes[E2BouquetList.SKIN_COMPONENT_KEY]
		listsmallHeight = sizes.get(E2BouquetList.SKIN_COMPONENT_LISTSMALL_HEIGHT, 30)
		instance.setItemHeight(listsmallHeight)

	def buildList(self,listnew):
		self.list=[]
		sizes = componentSizes[E2BouquetList.SKIN_COMPONENT_KEY]
		servicenameHeight = sizes.get(E2BouquetList.SKIN_COMPONENT_SERVICENAME_HEIGHT, 30)		
		width = self.l.getItemSize().width()
		for bouquets in listnew:
			res = [ bouquets ]
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 0, width, servicenameHeight, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, bouquets.servicename))
			self.list.append(res)
		self.l.setList(self.list)
		self.moveToIndex(0)

class E2ChannelList(MenuList):
	SKIN_COMPONENT_KEY = "PartnerboxList"
	SKIN_COMPONENT_LISTBIG_HEIGHT = "listbigHeight"
	SKIN_COMPONENT_SERVICENAME_HEIGHT = "servicenameHeight"
	SKIN_COMPONENT_NAME_HEIGHT = "nameHeight"
	SKIN_COMPONENT_STATE_WIDTH = "stateWidth"	
	
	def __init__(self, list, selChangedCB=None, enableWrapAround = True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.onSelChanged = [ ]
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		tlf = TemplatedListFonts()
		self.l.setFont(0, gFont(tlf.face(tlf.MEDIUM), tlf.size(tlf.MEDIUM)))
		self.l.setFont(1, gFont(tlf.face(tlf.SMALL), tlf.size(tlf.SMALL)))
	def postWidgetCreate(self, instance):
		MenuList.postWidgetCreate(self, instance)
		sizes = componentSizes[E2ChannelList.SKIN_COMPONENT_KEY]
		listbigHeight = sizes.get(E2ChannelList.SKIN_COMPONENT_LISTBIG_HEIGHT, 70)
		self.l.setItemHeight(listbigHeight)
		self.selectionChanged_conn = instance.selectionChanged.connect(self.selectionChanged)
	
	def preWidgetRemove(self, instance):
		self.selectionChanged_conn = None
		
	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()
				
	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()
		
	def moveSelectionTo(self,index):
		self.moveToIndex(index)

	def moveSelection(self, how):
		 self.instance.moveSelection(how)

	def buildList(self,listnew):
		self.list=[]
		sizes = componentSizes[E2ChannelList.SKIN_COMPONENT_KEY]
		servicenameHeight = sizes.get(E2ChannelList.SKIN_COMPONENT_SERVICENAME_HEIGHT, 28)
		nameHeight = sizes.get(E2ChannelList.SKIN_COMPONENT_NAME_HEIGHT, 20)	
		stateWidth = sizes.get(E2ChannelList.SKIN_COMPONENT_STATE_WIDTH, 150)		
		width = self.l.getItemSize().width()
		for epgdata in listnew:
			res = [ epgdata ]
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, 1, width, servicenameHeight, 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, epgdata.servicename))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, servicenameHeight, width, nameHeight, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, epgdata.eventtitle))
			if epgdata.eventstart != 0:
				endtime = int(epgdata.eventstart + epgdata.eventduration)
				res.append((eListboxPythonMultiContent.TYPE_TEXT, 5, servicenameHeight+nameHeight, width-stateWidth, nameHeight, 1, RT_HALIGN_LEFT|RT_VALIGN_CENTER, (("%s ... %s (%d " + _("mins") + ")") % (FuzzyTime(epgdata.eventstart)[1], FuzzyTime(endtime)[1], (endtime - epgdata.eventstart) / 60))))
			self.list.append(res)
		self.l.setList(self.list)
		self.moveToIndex(0)

class E2EPGList(MenuList):
	SKIN_COMPONENT_KEY = "PartnerboxList"
	SKIN_COMPONENT_LISTSMALL_HEIGHT = "listsmallHeight"
	SKIN_COMPONENT_CLOCK_HEIGHT = "clockHeight"
	SKIN_COMPONENT_CLOCK_WIDTH = "clockWidth"
	SKIN_COMPONENT_CLOCK_HPOS = "clockHPos"
	SKIN_COMPONENT_WEEKDAY_MARGIN = "weekdayMargin"
	SKIN_COMPONENT_ITEM_MARGIN = "itemMargin"
	
	def __init__(self, list, selChangedCB=None, enableWrapAround = True):
		MenuList.__init__(self, list, enableWrapAround, eListboxPythonMultiContent)
		self.onSelChanged = [ ]
		if selChangedCB is not None:
			self.onSelChanged.append(selChangedCB)
		tlf = TemplatedListFonts()
		self.l.setFont(0, gFont(tlf.face(tlf.BIG), tlf.size(tlf.BIG)))
		self.l.setFont(1, gFont(tlf.face(tlf.SMALLER), tlf.size(tlf.SMALLER)))
		self.days = [ _("Mon"), _("Tue"), _("Wed"), _("Thu"), _("Fri"), _("Sat"), _("Sun") ]
		self.timer_list = []
		self.clock_pixmap = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock.png'))
		self.clock_add_pixmap = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_add.png'))
		self.clock_pre_pixmap = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_pre.png'))
		self.clock_post_pixmap = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_post.png'))
		self.clock_prepost_pixmap = LoadPixmap(resolveFilename(SCOPE_CURRENT_SKIN, 'skin_default/icons/epgclock_prepost.png'))
		
	def postWidgetCreate(self, instance):
		MenuList.postWidgetCreate(self, instance)
		sizes = componentSizes[E2EPGList.SKIN_COMPONENT_KEY]
		listsmallHeight = sizes.get(E2EPGList.SKIN_COMPONENT_LISTSMALL_HEIGHT, 30)
		instance.setItemHeight(listsmallHeight)
		self.selectionChanged_conn = instance.selectionChanged.connect(self.selectionChanged)
	
	def preWidgetRemove(self, instance):
		self.sectionChanged_conn = None
	
	def getCurrentIndex(self):
		return self.instance.getCurrentIndex()
		
	def moveSelectionTo(self,index):
		self.moveToIndex(index)
		
	def selectionChanged(self):
		for x in self.onSelChanged:
			if x is not None:
				x()
	
	def buildList(self,listnew, timerlist):
		self.list=[]
		self.timer_list = timerlist
		for epgdata in listnew:	
			res = [ epgdata ]
			rec=epgdata.eventstart and (self.isInTimer(epgdata.eventstart, epgdata.eventduration, epgdata.servicereference))
			sizes = componentSizes[E2EPGList.SKIN_COMPONENT_KEY]
			clockWidth = sizes.get(E2EPGList.SKIN_COMPONENT_CLOCK_WIDTH, 21)
			clockHeight = sizes.get(E2EPGList.SKIN_COMPONENT_CLOCK_HEIGHT, 21)
			clockHPos = sizes.get(E2EPGList.SKIN_COMPONENT_CLOCK_HPOS, 5)
			weekdayMargin = sizes.get(E2EPGList.SKIN_COMPONENT_WEEKDAY_MARGIN, 70)
			self._itemMargin = sizes.get(E2EPGList.SKIN_COMPONENT_ITEM_MARGIN, 10)
			esize = self.l.getItemSize()
			width = esize.width()
			height = esize.height()
			weekday_width = int(width * 0.08)
			datetime_x = weekday_width + self._itemMargin - weekdayMargin
			datetime_width = int(width * 0.23)
			desc_x = datetime_x + datetime_width + self._itemMargin
			desc_width = width - desc_x - self._itemMargin
			r1 = Rect(0, 0, weekday_width, height)
			r2 = Rect(datetime_x, 0, datetime_width, height)
			r3 = Rect(desc_x, 0, desc_width, height)
			t = localtime(epgdata.eventstart)
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r1.left(), r1.top(), r1.width(), r1.height(), 0, RT_HALIGN_RIGHT|RT_VALIGN_CENTER, self.days[t[6]]))
			res.append((eListboxPythonMultiContent.TYPE_TEXT, r2.left(), r2.top(), r2.width(), r1.height(), 0, RT_HALIGN_RIGHT|RT_VALIGN_CENTER, "%02d.%02d, %02d:%02d"%(t[2],t[1],t[3],t[4])))
			if rec:
				clock_pic = self.getClockPixmap(epgdata.servicereference, epgdata.eventstart, epgdata.eventduration, epgdata.eventid)
				res.append((eListboxPythonMultiContent.TYPE_PIXMAP_ALPHABLEND, r3.left(), clockHPos, clockWidth, clockHeight, clock_pic))
				res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.left() + clockWidth + self._itemMargin, r3.top(), r3.width(), r3.height(), 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, epgdata.eventtitle))
			else:
				res.append((eListboxPythonMultiContent.TYPE_TEXT, r3.left(), r3.top(), r3.width(), r3.height(), 0, RT_HALIGN_LEFT|RT_VALIGN_CENTER, epgdata.eventtitle))
			
			self.list.append(res)
		self.l.setList(self.list)
		self.moveToIndex(0)
		
	def isInTimer(self, begin, duration, service):
		time_match = 0
		chktime = None
		chktimecmp = None
		chktimecmp_end = None
		end = begin + duration
		for x in self.timer_list:
			if x.servicereference.upper() == service.upper():
				if x.repeated != 0:
					if chktime is None:
						chktime = localtime(begin)
						chktimecmp = chktime.tm_wday * 1440 + chktime.tm_hour * 60 + chktime.tm_min
						chktimecmp_end = chktimecmp + (duration / 60)
					time = localtime(x.timebegin)
					for y in range(7):
						if x.repeated & (2 ** y):
							timecmp = y * 1440 + time.tm_hour * 60 + time.tm_min
							if timecmp <= chktimecmp < (timecmp + ((x.timeend - x.timebegin) / 60)):
								time_match = ((timecmp + ((x.timeend - x.timebegin) / 60)) - chktimecmp) * 60
							elif chktimecmp <= timecmp < chktimecmp_end:
								time_match = (chktimecmp_end - timecmp) * 60
				else: 
					if begin <= x.timebegin <= end:
						diff = end - x.timebegin
						if time_match < diff:
							time_match = diff
					elif x.timebegin <= begin <= x.timeend:
						diff = x.timeend - begin
						if time_match < diff:
							time_match = diff
				if time_match:
					break
		return time_match
	
	def getClockPixmap(self, refstr, beginTime, duration, eventId):

		pre_clock = 1
		post_clock = 2
		clock_type = 0
		endTime = beginTime + duration
		for x in self.timer_list:
			if x.servicereference.upper() == refstr.upper():
				#if x.eventId == eventId:
				if x.eit == eventId:
					return self.clock_pixmap
				beg = x.timebegin
				end = x.timeend
				if beginTime > beg and beginTime < end and endTime > end:
					clock_type |= pre_clock
				elif beginTime < beg and endTime > beg and endTime < end:
					clock_type |= post_clock
		if clock_type == 0:
			return self.clock_add_pixmap
		elif clock_type == pre_clock:
			return self.clock_pre_pixmap
		elif clock_type == post_clock:
			return self.clock_post_pixmap
		else:
			return self.clock_prepost_pixmap

class RemoteTimerEventView(Screen):
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2
	skin = """
		<screen name="RemoteTimerEventView" position="center,120" size="950,520" title="Eventview">
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="210,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="410,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="610,5" size="200,40" alphatest="on" />
			<widget name="key_red" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_green" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_yellow" position="410,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_blue" position="610,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<eLabel position="10,50" size="930,1" backgroundColor="grey" />
			<widget name="epg_description" position="10,60" size="930,400" font="Regular;22" />
			<widget name="datetime" position="10,480" size="200,25" font="Regular;22" />
			<widget name="duration" position="220,480" size="200,25" font="Regular;22" />
			<widget name="channel" position="430,480" size="500,25" font="Regular;22" halign="right" />
		</screen>"""
	
	def __init__(self, session, E2Timerlist, epgdata , partnerboxentry):
		self.session = session
		Screen.__init__(self, session)
		self["epg_description"] = ScrollLabel()
		self["datetime"] = Label()
		self["channel"] = Label()
		self["duration"] = Label()
		self["key_red"] = Label() # Dummy, kommt eventuell noch was
		self["key_green"] = Label() # Dummy, kommt eventuell noch was
		self["key_yellow"] = Label() # Dummy, kommt eventuell noch was
		self["key_blue"] = Label() # Dummy, kommt eventuell noch was
		self.key_green_choice = self.ADD_TIMER
		self.onLayoutFinish.append(self.startRun)
		self.E2TimerList = E2Timerlist
		self.epgdata = epgdata
		
		self["actions"] = ActionMap(["WizardActions", "DirectionActions", "ColorActions", "EventViewActions"],
		{
			"back": self.close,
			"pageUp": self.pageUp,
			"pageDown": self.pageDown,
		}, -1)

		self.PartnerboxEntry = partnerboxentry
		self.password = partnerboxentry.password.value
		self.username = "root"
		try:
			self.webiftype = partnerboxentry.webinterfacetype.value
		except:
			self.webiftype = "standard"
		self.ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
		port = partnerboxentry.port.value
		self.http = "http://%s:%d" % (self.ip,port)
		self.useinternal = int(partnerboxentry.useinternal.value)

	def startRun(self):
		name = self.epgdata.servicename
		if name != "n/a" and name != "<n/a>":
			self["channel"].setText(name)
		else:
			self["channel"].setText(_("unknown service"))
		text = self.epgdata.eventtitle
		short = self.epgdata.eventdescription
		ext = self.epgdata.eventdescriptionextended
		if len(short) > 0 and short != text:
			text = text + '\n\n' + short
		if len(ext) > 0:
			if len(text) > 0:
				text = text + '\n\n'
			text = text + ext
		self.setTitle(self.epgdata.eventtitle)
		self["epg_description"].setText(text)
		endtime = int(self.epgdata.eventstart + self.epgdata.eventduration)
		t = localtime(self.epgdata.eventstart)
		datetime = ("%02d.%02d, %02d:%02d"%(t[2],t[1],t[3],t[4]))
		duration = (" (%d " + _("mins")+")") % ((self.epgdata.eventduration ) / 60)
		self["datetime"].setText(datetime)
		self["duration"].setText(duration)
		self["key_red"].setText("")	

	def pageUp(self):
		self["epg_description"].pageUp()

	def pageDown(self):
		self["epg_description"].pageDown()

###########################################
# ChannelContextMenu
###########################################
from Screens.ChannelSelection import ChannelContextMenu, OFF, MODE_TV
from Components.ChoiceList import ChoiceEntryComponent
from Tools.BoundFunction import boundFunction

def autostart_ChannelContextMenu(session, **kwargs):
	partnerboxChannelContextMenuInit()

baseChannelContextMenu__init__ = None
def partnerboxChannelContextMenuInit():
	global baseChannelContextMenu__init__
	if baseChannelContextMenu__init__ is None:
		baseChannelContextMenu__init__ = ChannelContextMenu.__init__
	ChannelContextMenu.__init__ = partnerboxChannelContextMenu__init__
	# new methods
	ChannelContextMenu.addPartnerboxService = addPartnerboxService
	ChannelContextMenu.callbackPartnerboxServiceList = callbackPartnerboxServiceList
	ChannelContextMenu.startAddParnerboxService = startAddParnerboxService
	ChannelContextMenu.setPartnerboxService = setPartnerboxService
	ChannelContextMenu.setParentalControlPin = setParentalControlPin
	ChannelContextMenu.parentalControlPinEntered = parentalControlPinEntered

def partnerboxChannelContextMenu__init__(self, session, csel):
	baseChannelContextMenu__init__(self, session, csel)
	if csel.mode == MODE_TV:
		current_root = csel.getRoot()
		inBouquetRootList = current_root and current_root.getPath().find('FROM BOUQUET "bouquets.') != -1 #FIXME HACK
		inBouquet = csel.getMutableList() is not None
		if csel.bouquet_mark_edit == OFF and not csel.movemode:
			if not inBouquetRootList:
				if inBouquet:
					if config.ParentalControl.configured.value:
						callFunction = self.setParentalControlPin
					else:
						callFunction = self.addPartnerboxService
					self["menu"].list.insert(1, ChoiceEntryComponent(text = (_("add Partnerbox service"), boundFunction(callFunction,0))))
			if (not inBouquetRootList and not inBouquet) or (inBouquetRootList):
				if config.usage.multibouquet.value:
					if config.ParentalControl.configured.value:
						callFunction = self.setParentalControlPin
					else:
						callFunction = self.addPartnerboxService
					self["menu"].list.insert(1, ChoiceEntryComponent(text = (_("add Partnerbox bouquet"), boundFunction(callFunction,1))))

def addPartnerboxService(self, insertType):
	count = config.plugins.Partnerbox.entriescount.value
	if count == 1:
		self.startAddParnerboxService(insertType, None, None, config.plugins.Partnerbox.Entries[0])
	else:
		self.session.openWithCallback(boundFunction(self.startAddParnerboxService,insertType), PartnerboxEntriesListConfigScreen, 0)

def startAddParnerboxService(self, insertType, session, what, partnerboxentry = None):
	if partnerboxentry is None:
		self.close()
	else:
		self.session.openWithCallback(self.callbackPartnerboxServiceList, PartnerBouquetList, [], partnerboxentry, 1, insertType)

def setParentalControlPin(self, insertType):
		self.session.openWithCallback(boundFunction(self.parentalControlPinEntered, insertType), PinInput, pinList = [config.ParentalControl.servicepin[0].value], triesEntry = config.ParentalControl.retries.servicepin, title = _("Enter the service pin"), windowTitle = _("Change pin code"))

def parentalControlPinEntered(self, insertType, result):
		if result:
			self.addPartnerboxService(insertType)
		else:
			self.session.openWithCallback(self.close, MessageBox, _("The pin code you entered is wrong."), MessageBox.TYPE_ERROR)

def callbackPartnerboxServiceList(self, result): 
	if result and result[1]:
		isBouquet = result[0]
		partnerboxentry = result[2]
		if isBouquet == 0:
			servicelist = result[1]
			item = servicelist[0]
			current_root = self.csel.getRoot()
			mutableList = self.csel.getMutableList(current_root)
			if not mutableList is None:
				service = self.setPartnerboxService(item, partnerboxentry)
				if not mutableList.addService(service):
					self.csel.bouquetNumOffsetCache = { }
					mutableList.flushChanges()
					self.csel.servicelist.addService(service)
		elif isBouquet == 1:
			servicelist = result[1][0]
			bouquet = result[1][1]
			services = []
			for item in servicelist:
				services.append(self.setPartnerboxService(item, partnerboxentry))
			self.csel.addBouquet("%s (%s)" % (bouquet.servicename.replace("(TV)",""), partnerboxentry.name.value), services)
	self.close()

def setPartnerboxService(self, item, partnerboxentry):
	password = partnerboxentry.password.value
	ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
	port = 8001
	if password:
		http = "http://root:%s@%s:%d/%s" % (password,ip,port, item.servicereference)
	else:
		http = "http://%s:%d/%s" % (ip,port, item.servicereference)
	service = eServiceReference(item.servicereference)
	service.setPath(http)
	service.setName("%s (%s)" % (item.servicename, partnerboxentry.name.value))
	return service	

class PartnerBouquetList(Screen):
	skin = """
		<screen name="PartnerBouquetList" position="center,center" size="400,420" title="Choose bouquet">
		<widget name="text" position="10,10" zPosition="1" size="380,390" font="Regular;20" halign="center" valign="center" />
		<widget name="bouquetlist" position="10,10" zPosition="2" size="380,390" enableWrapAround="1" scrollbarMode="showOnDemand" />
	</screen>"""
	def __init__(self, session, E2Timerlist, partnerboxentry, playeronly, insertType):
		self.session = session
		Screen.__init__(self, session)
		self["bouquetlist"] = E2BouquetList([])	
		self["text"] = Label(_("Getting Partnerbox Bouquet Information..."))	
		self.onLayoutFinish.append(self.startRun)	
		self.E2TimerList = E2Timerlist		
		self.useinternal = 0 # always use partnerbox services
		self.insertType = insertType
		self["actions"] = ActionMap(["WizardActions", "DirectionActions"],
		{
			"ok": self.action,
			"back": self.closeScreen,
		}, -1)
		
		self.PartnerboxEntry = partnerboxentry
		self.password = partnerboxentry.password.value
		self.username = "root"
		try:
			self.webiftype = partnerboxentry.webinterfacetype.value
		except:
			self.webiftype = "standard"
		ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
		port = partnerboxentry.port.value
		self.http = "http://%s:%d" % (ip,port)
		self.playeronly = playeronly
		self.url = self.http + "/web/getservices"	

	def action(self):
		if self.insertType == 0:
			try:
				sel = self["bouquetlist"].l.getCurrentSelection()[0]
				if sel is None:
					return
				self.session.openWithCallback(self.callbackChannelList, PartnerChannelList, self.E2TimerList, sel.servicereference, sel.servicename, self.PartnerboxEntry, self.playeronly)
			except: return
		else:
			self.takeBouquet()

	def callbackChannelList(self, result):
		self.close((0, result, self.PartnerboxEntry))

	def closeScreen(self):
		self.close(None)

	def takeBouquet(self):
		sel = None
		try:
			sel = self["bouquetlist"].l.getCurrentSelection()[0]
			if sel is None:
				return
		except: return
		ref = urllib.quote(sel.servicereference.decode('utf8').encode('latin-1','ignore'))
		url = self.http + "/web/epgnow?bRef=" + ref
		sendPartnerBoxWebCommand(url, 10, self.username, self.password, self.webiftype).addCallback(self.ChannelListDownloadCallback, sel).addErrback(self.ChannelListDownloadError)

	def ChannelListDownloadCallback(self, xmlstring, sel):
		e2ChannelList = []
		if xmlstring:
			root = xml.etree.cElementTree.fromstring(xmlstring)
			for events in root.findall("e2event"):
				servicereference = str(events.findtext("e2eventservicereference", '').encode("utf-8", 'ignore'))
				servicename = str(events.findtext("e2eventservicename", 'n/a').encode("utf-8", 'ignore'))
				e2ChannelList.append(E2EPGListAllData(servicereference = servicereference, servicename = servicename))
		result = (e2ChannelList, sel)
		self.close((1, result, self.PartnerboxEntry))

	def ChannelListDownloadError(self, error = None):
		if error is not None:
			self["text"].setText(str(error.getErrorMessage()))
			
	def startRun(self):
		self["bouquetlist"].instance.hide()
		self.getBouquetList()
	
	def getBouquetList(self):
		sendPartnerBoxWebCommand(self.url, 10, self.username, self.password, self.webiftype).addCallback(self.downloadCallback).addErrback(self.ChannelListDownloadError)
		
	def downloadCallback(self, callback = None):
		self.readXML(callback)
		self["bouquetlist"].instance.show()

	def readXML(self, xmlstring):
		BouquetList = []
		root = xml.etree.cElementTree.fromstring(xmlstring)
		for servives in root.findall("e2service"):
			BouquetList.append(E2ServiceList(
			servicereference = str(servives.findtext("e2servicereference", '').encode("utf-8", 'ignore')),
			servicename = str(servives.findtext("e2servicename", 'n/a').encode("utf-8", 'ignore'))))
		self["bouquetlist"].buildList(BouquetList)		

class PartnerChannelList(Screen):
	EMPTY = 0
	ADD_TIMER = 1
	REMOVE_TIMER = 2
	REMOTE_TIMER_MODE = 0
	REMOTE_TV_MODE = 1
	skin = """
		<screen name="PartnerChannelList" position="center,120" size="950,520" title="Channel List">
			<ePixmap pixmap="skin_default/buttons/red.png" position="10,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/green.png" position="210,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/yellow.png" position="410,5" size="200,40" alphatest="on" />
			<ePixmap pixmap="skin_default/buttons/blue.png" position="610,5" size="200,40" alphatest="on" />
			<widget name="key_red" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_green" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_yellow" position="410,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#a08500" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="key_blue" position="610,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#18188b" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<eLabel position="10,50" size="930,1" backgroundColor="grey" />
			<widget name="channellist" position="10,70" size="930,420" zPosition="2" enableWrapAround="1" scrollbarMode="showOnDemand" />
			<widget name="text" position="10,60" size="930,450" zPosition="1" font="Regular;20" halign="center" valign="center" />
		</screen>"""
	def __init__(self, session, E2Timerlist, ServiceReference, ServiceName, partnerboxentry, playeronly):
		self.skinName = "PartnerChannelList"
		self.session = session
		Screen.__init__(self, session)
		
		self["channellist"] = E2ChannelList([], selChangedCB = self.onSelectionChanged)		
		self.playeronly = playeronly		
		self.useinternal = 0 # always use partnerbox services
		self.partnerboxentry = partnerboxentry
		self["actions"] = ActionMap(["WizardActions", "DirectionActions", "ColorActions"],
		{
			"ok": self.getEntry,
			"back": self.closeScreen,
			"yellow": self.getEpg,
			"blue": self.EPGEvent,
			"red": self.closeScreen,
			"green": self.getEntry,
		}, -1)
		self["key_green"] = Label()
		self["key_green"].setText(_("Apply"))
		self.key_green_choice = self.EMPTY
		self["key_yellow"] = Label()
		self["key_red"] = Label(_("Abort"))
		self["key_blue"] = Label(_("Info"))		
		self["text"] = Label(_("Getting Channel Information..."))		
		self.onLayoutFinish.append(self.startRun)
		self.E2TimerList = E2Timerlist
		self.E2ChannelList = []
		self.servicereference = ServiceReference		

		self.password = partnerboxentry.password.value
		self.username = "root"
		try:
			self.webiftype = partnerboxentry.webinterfacetype.value
		except:
			self.webiftype = "standard"
		self.ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
		self.port = partnerboxentry.port.value
		self.http = "http://%s:%d" % (self.ip,self.port)
		self.ChannelListCurrentIndex = 0
		self.mode = self.REMOTE_TIMER_MODE

	def startRun(self):
		self["channellist"].instance.hide()
		self.getChannelList()		

	def onSelectionChanged(self):
		pass

	def getEpg(self):
		if self.playeronly == 0:
			cur = self["channellist"].l.getCurrentSelection()[0]
			self.session.openWithCallback(self.getEpgCallback, RemoteTimerEPGList, self.E2TimerList, cur.servicereference, cur.servicename, self.partnerboxentry, False)

	def getEpgCallback(self, result):
		if len(result)>0:
			if result[0].servicename == "<n/a>":
				name = self["channellist"].l.getCurrentSelection()[0].servicename
				result[0].servicename = name
		self.close(result)

	def doNothing(self):
		pass

	def getEntry(self):
		sel = None
		try:
			sel = self["channellist"].l.getCurrentSelection()[0]
		except:return
		if sel is None:
			return
		self.close([sel])

	def closeScreen(self):
		self.close(None)
		
	def getChannelList(self):
		ref = urllib.quote(self.servicereference.decode('utf8').encode('latin-1','ignore'))
		url = self.http + "/web/epgnow?bRef=" + ref
		sendPartnerBoxWebCommand(url, 10, self.username, self.password, self.webiftype).addCallback(self.ChannelListDownloadCallback).addErrback(self.ChannelListDownloadError)		
		
	def ChannelListDownloadCallback(self, callback = None):
		self.readXMLServiceList(callback)
		if self.ChannelListCurrentIndex !=0:
			sel = self["channellist"].moveSelectionTo(self.ChannelListCurrentIndex)
			self.ChannelListCurrentIndex = 0
		self["channellist"].instance.show()

	def ChannelListDownloadError(self, error = None):
		if error is not None:
			self["text"].setText(str(error.getErrorMessage()))
			self.mode = REMOTE_TIMER_MODE
			
	def readXMLServiceList(self, xmlstring):
		self.E2ChannelList = []
		root = xml.etree.cElementTree.fromstring(xmlstring)
		for events in root.findall("e2event"):
			servicereference = str(events.findtext("e2eventservicereference", '').encode("utf-8", 'ignore'))
			servicename = str(events.findtext("e2eventservicename", 'n/a').encode("utf-8", 'ignore'))
			try:eventstart = int(events.findtext("e2eventstart", 0))
			except:eventstart = 0
			try:eventduration = int(events.findtext("e2eventduration", 0))
			except:eventduration  = 0
			try:eventtitle = str(events.findtext("e2eventtitle", '').encode("utf-8", 'ignore'))
			except:eventtitle = ""
			try:eventid = int(events.findtext("e2eventid", 0))
			except:eventid = 0
			try:eventdescription = str(events.findtext("e2eventdescription", '').encode("utf-8", 'ignore'))
			except:eventdescription = ""
			try:eventdescriptionextended = str(events.findtext("e2eventdescriptionextended", '').encode("utf-8", 'ignore'))
			except:eventdescriptionextended = ""
			self.E2ChannelList.append(E2EPGListAllData(
					servicereference = servicereference, servicename = servicename, eventstart = eventstart,
					eventduration = eventduration, eventtitle = eventtitle, eventid = eventid, eventdescription= eventdescription, 
					eventdescriptionextended = eventdescriptionextended))
		self["channellist"].buildList(self.E2ChannelList)
		
	def EPGEvent(self):
		sel = self["channellist"].l.getCurrentSelection()[0]
		if sel is None:
			return
		self.session.openWithCallback(self.CallbackEPGEvent, RemoteTimerEventView, self.E2TimerList, sel, self.partnerboxentry)
		
	def CallbackEPGEvent(self):
		pass
		
	def onSelectionChanged(self):
		cur = self["channellist"].getCurrent()
		if cur is None:
			self["key_green"].setText("")
			self.key_green_choice = self.EMPTY
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			return
		eventid = cur[0].eventid
		if eventid ==0:
			self.key_green_choice = self.EMPTY
			self["key_yellow"].setText("")
			self["key_blue"].setText("")
			return
		if self.playeronly == 0:
			self["key_yellow"].setText(_("EPG Selection"))
		self["key_blue"].setText(_("Info"))
		serviceref = cur[0].servicereference