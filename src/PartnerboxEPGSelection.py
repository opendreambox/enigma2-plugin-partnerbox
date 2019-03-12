
#  Partnerbox E2
#
#  $Id$
#
#  Coded by Dr.Best (c) 2009
#  Support: board.dreambox.tools
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

from Screens.Screen import Screen
from Screens.MessageBox import MessageBox
from Components.config import config
from PartnerboxSetup import PartnerboxEntriesListConfigScreen
from Screens.EpgSelection import EPGSelection
from Components.EpgList import EPG_TYPE_SINGLE, EPG_TYPE_SIMILAR, EPG_TYPE_MULTI
from Tools.BoundFunction import boundFunction
from PartnerboxFunctions import SetPartnerboxTimerlist, isInTimerList, sendPartnerBoxWebCommand, FillE2TimerList
import PartnerboxFunctions as partnerboxfunctions
from enigma import eServiceReference, eServiceCenter

baseEPGSelection__init__ = None
baseonSelectionChanged = None
basetimerAdd = None
basefinishedAdd = None
baseonCreate = None

def Partnerbox_EPGSelectionInit():
	global baseEPGSelection__init__, baseonSelectionChanged, basetimerAdd, basefinishedAdd, baseonCreate
	if baseEPGSelection__init__ is None:
		baseEPGSelection__init__ = EPGSelection.__init__
	if baseonSelectionChanged is None:
		baseonSelectionChanged = EPGSelection.onSelectionChanged
	if basetimerAdd is None:
		basetimerAdd = EPGSelection.timerAdd
	if basefinishedAdd is None:
		basefinishedAdd = EPGSelection.finishedAdd
	if baseonCreate is None:
		baseonCreate = EPGSelection.onCreate

	EPGSelection.__init__ = Partnerbox_EPGSelection__init__
	EPGSelection.onSelectionChanged = Partnerbox_onSelectionChanged
	EPGSelection.timerAdd = Partnerbox_timerAdd
	EPGSelection.finishedAdd = Partnerbox_finishedAdd
	EPGSelection.onCreate = Partnerbox_onCreate
	# new methods
	EPGSelection.PartnerboxSelection = PartnerboxSelection
	EPGSelection.RedButtonText = RedButtonText
	EPGSelection.NewPartnerBoxSelected = NewPartnerBoxSelected
	EPGSelection.GetPartnerboxTimerlistCallback = GetPartnerboxTimerlistCallback
	EPGSelection.GetPartnerboxTimerlistCallbackError = GetPartnerboxTimerlistCallbackError
	EPGSelection.CheckRemoteTimer = CheckRemoteTimer
	EPGSelection.DeleteTimerConfirmed = DeleteTimerConfirmed
	EPGSelection.DeleteTimerCallback = DeleteTimerCallback
	EPGSelection.GetPartnerboxTimerlist = GetPartnerboxTimerlist
	EPGSelection.PartnerboxInit = PartnerboxInit

def Partnerbox_EPGSelection__init__(self, session, service, zapFunc=None, eventid=None, bouquetChangeCB=None, serviceChangeCB=None):
	#check if alternatives are defined
	if isinstance(service, eServiceReference):
		if service.flags & (eServiceReference.isGroup):
			service = eServiceCenter.getInstance().list(eServiceReference("%s" %(service.toString()))).getContent("S")[0]
	baseEPGSelection__init__(self, session, service, zapFunc, eventid, bouquetChangeCB, serviceChangeCB)
	self.PartnerboxInit(True)
	self._pluginListRed.insert(0,("Partnerbox" if self.partnerboxentry is None else self.partnerboxentry.name.value, self.PartnerboxSelection))
	self.RedButtonText()

def PartnerboxInit(self, filterRef):
	self.filterRef = filterRef
	self.partnerboxentry = None
	partnerboxfunctions.remote_timer_list = []
	if int(config.plugins.Partnerbox.entriescount.value) >= 1:
		try: 
			self.partnerboxentry = config.plugins.Partnerbox.Entries[0]
			partnerboxfunctions.CurrentIP = self.partnerboxentry.ip.value
		except: self.partnerboxentry = None

def NewPartnerBoxSelected(self, session, what, partnerboxentry = None):
	if partnerboxentry is not None:
		self.partnerboxentry = partnerboxentry
		curService = None
		if self.type == EPG_TYPE_SINGLE and self.filterRef:
			curService = self.currentService.ref.toString()
		SetPartnerboxTimerlist(partnerboxentry, curService)
		Partnerbox_onSelectionChanged(self)
		del self._pluginListRed[0]
		self._pluginListRed.insert(0,(self.partnerboxentry.name.value, self.PartnerboxSelection))
		self.RedButtonText()
		self["list"].l.invalidate() # immer zeichnen, da neue Box ausgewaehlt wurde

def Partnerbox_onSelectionChanged(self):
	baseonSelectionChanged(self)
	self.CheckRemoteTimer()

def Partnerbox_timerAdd(self):
	proceed = True
	if self.key_green_choice == self.REMOVE_TIMER:
		cur = self["list"].getCurrent()
		event = cur[0]
		serviceref = cur[1]
		if event is not None:
			timerentry = isInTimerList(event.getBeginTime(), event.getDuration(),serviceref.ref.toString(), event.getEventId(), partnerboxfunctions.remote_timer_list)
			if timerentry is not None:
				proceed = False
				name = timerentry.name
				self.session.openWithCallback(boundFunction(self.DeleteTimerConfirmed,timerentry), MessageBox, _("Do you really want to delete the timer \n%s ?") % name)
	if proceed:basetimerAdd(self)

def Partnerbox_finishedAdd(self, answer):
	basefinishedAdd(self,answer)
	self.CheckRemoteTimer()

def Partnerbox_onCreate(self):
	baseonCreate(self)
	self.GetPartnerboxTimerlist()

def GetPartnerboxTimerlist(self):
	if self.partnerboxentry is not None:
		ip = "%d.%d.%d.%d" % tuple(self.partnerboxentry.ip.value)
		port = self.partnerboxentry.port.value
		http = "http://%s:%d" % (ip,port)
		sCommand = http + "/web/timerlist"
		sendPartnerBoxWebCommand(sCommand, 3, "root", self.partnerboxentry.password.value, self.partnerboxentry.webinterfacetype.value).addCallback(boundFunction(self.GetPartnerboxTimerlistCallback)).addErrback(boundFunction(self.GetPartnerboxTimerlistCallbackError))

def GetPartnerboxTimerlistCallback(self, result):
	sxml = result
	if sxml is not None:
		curService = None
		if self.type == EPG_TYPE_SINGLE and self.filterRef:
			curService = self.currentService.ref.toString()
		partnerboxfunctions.remote_timer_list = FillE2TimerList(sxml, curService)
	Partnerbox_onSelectionChanged(self)
	self["list"].l.invalidate()

def GetPartnerboxTimerlistCallbackError(self, error = None):
	if error is not None:
		print str(error.getErrorMessage())
		msg = self.session.open(MessageBox, error.getErrorMessage(), MessageBox.TYPE_ERROR)
		msg.setTitle(_("Partnerbox"))

def CheckRemoteTimer(self):
	if self.key_green_choice != self.REMOVE_TIMER:
		cur = self["list"].getCurrent()
		if cur is None:
			return
		event = cur[0]
		serviceref = cur[1]
		if event is not None:
			timerentry = isInTimerList(event.getBeginTime(), event.getDuration(),serviceref.ref.toString(),event.getEventId(), partnerboxfunctions.remote_timer_list)
			if timerentry is not None:
				self["key_green"].setText(_("Remove timer"))
				self.key_green_choice = self.REMOVE_TIMER

def DeleteTimerConfirmed (self, timerentry, answer):
	if answer:
		ip = "%d.%d.%d.%d" % tuple(self.partnerboxentry.ip.value)
		port = self.partnerboxentry.port.value
		http = "http://%s:%d" % (ip,port)
		sCommand = http + "/web/timerdelete?sRef=" + timerentry.servicereference + "&begin=" + ("%s"%(timerentry.timebegin)) + "&end=" +("%s"%(timerentry.timeend))
		sendPartnerBoxWebCommand(sCommand, 3, "root", self.partnerboxentry.password.value, self.partnerboxentry.webinterfacetype.value).addCallback(self.DeleteTimerCallback).addErrback(boundFunction(DeleteTimerCallbackError,self))

def DeleteTimerCallback(self, callback = None):
	curService = None
	self.GetPartnerboxTimerlist()

def DeleteTimerCallbackError(self, error = None):
	if error is not None:
		msg = self.session.open(MessageBox, error.getErrorMessage(), MessageBox.TYPE_ERROR)
		msg.setTitle(_("Partnerbox"))

def PartnerboxSelection(self, session, event, currentService):
	session.openWithCallback(self.NewPartnerBoxSelected, PartnerboxEntriesListConfigScreen, 0)

def RedButtonText(self):
	if len(self._pluginListRed) > 1:
		self["key_red"].setText(_("More ..."))
	else:
		self["key_red"].setText("Partnerbox" if self.partnerboxentry is None else self.partnerboxentry.name.value)

