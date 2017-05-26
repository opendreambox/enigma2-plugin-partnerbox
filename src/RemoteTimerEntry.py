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

from Screens.Screen import Screen
import Screens.ChannelSelection
from ServiceReference import ServiceReference
from Components.config import config, ConfigSelection, ConfigText, ConfigSubList, ConfigDateTime, ConfigClock, ConfigYesNo, getConfigListEntry
from Components.ActionMap import NumberActionMap
from Components.ConfigList import ConfigListScreen
from Components.Label import Label
from Components.Pixmap import Pixmap
from RecordTimer import AFTEREVENT
from enigma import eEPGCache
from time import localtime, mktime, strftime
from datetime import datetime
from Screens.TimerEntry import TimerEntry
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
import urllib

import xml.etree.cElementTree

from PartnerboxFunctions import sendPartnerBoxWebCommand, getServiceRef, SetPartnerboxTimerlist
import PartnerboxFunctions as partnerboxfunctions
from time import localtime

class RemoteTimerEntry(Screen, ConfigListScreen):
	skin = """
		<screen name="RemoteTimerEntry" position="center,center" size="820,420" title="Remote timer entry">
			<widget name="cancel" pixmap="skin_default/buttons/red.png" position="10,5" size="200,40" alphatest="on" />
			<widget name="ok" pixmap="skin_default/buttons/green.png" position="210,5" size="200,40" alphatest="on" />
			<widget name="canceltext" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<widget name="oktext" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
			<eLabel position="10,50" size="800,1" backgroundColor="grey" />
			<widget name="config" position="10,60" size="800,330" enableWrapAround="1" scrollbarMode="showOnDemand" />
		</screen>"""

	def __init__(self, session, timer, Locations, partnerboxentry=None):
		self.session = session
		Screen.__init__(self, session)
		self.timer = timer
		self.Locations = Locations
	
		self.entryDate = None
		self.entryService = None
		self.partnerboxentry = partnerboxentry
		if self.partnerboxentry is not None:
			self.setTitle("Remote timer entry %s" %(self.partnerboxentry.name.value))
		self["oktext"] = Label(_("OK"))
		self["canceltext"] = Label(_("Cancel"))
		self["ok"] = Pixmap()
		self["cancel"] = Pixmap()
		self.createConfig()
		self["actions"] = NumberActionMap(["SetupActions", "GlobalActions", "PiPSetupActions"],
		{
			"save": self.keyGo,
			"cancel": self.keyCancel,
			"volumeUp": self.incrementStart,
			"volumeDown": self.decrementStart,
			"size+": self.incrementEnd,
			"size-": self.decrementEnd
		}, -2)
		self.list = []
		ConfigListScreen.__init__(self, self.list, session = session)
		self.createSetup("config")

	def createConfig(self):
		
		justplay = self.timer.justplay
		afterevent = {
			0: "nothing",
			2: "deepstandby",
			1: "standby",
			3: "auto"
			}[self.timer.afterEvent]
				
		weekday_table = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
		day = []
		weekday = 0
		for x in (0, 1, 2, 3, 4, 5, 6):
			day.append(0)
		begin = self.timer.timebegin
		end = self.timer.timeend
		weekday = (int(strftime("%w", localtime(begin))) - 1) % 7
		day[weekday] = 1
		name = self.timer.name 
		description = self.timer.description
		self.timerentry_justplay = ConfigSelection(choices = [("1", _("zap")), ("0", _("record"))], default = str(justplay))
		self.timerentry_afterevent = ConfigSelection(choices = [("nothing", _("do nothing")), ("standby", _("go to standby")), ("deepstandby", _("go to deep standby")), ("auto", _("auto"))], default = afterevent)
		self.timerentry_name = ConfigText(default = name, visible_width = 50, fixed_size = False)
		self.timerentry_description = ConfigText(default = description, visible_width = 50, fixed_size = False)
		self.timerentry_date = ConfigDateTime(default = begin, formatstring = _("%d.%B %Y"), increment = 86400)
		self.timerentry_starttime = ConfigClock(default = begin)
		self.timerentry_endtime = ConfigClock(default = end)
		self.timerentry_showendtime = ConfigSelection(default = ((self.timer.end - self.timer.begin) > 4), choices = [(True, _("yes")), (False, _("no"))])		
		#if self.timer.type == 0:
		default = self.timer.dirname
		if default == "None":
			if self.Locations:
				default = self.Locations[0]
			else:
				default = "N/A"
		if default not in self.Locations:
			self.Locations.append(default)
		self.timerentry_dirname = ConfigSelection(default = default, choices = self.Locations)
		self.timerentry_weekday = ConfigSelection(default = weekday_table[weekday], choices = [("mon",_("Monday")), ("tue", _("Tuesday")), ("wed",_("Wednesday")), ("thu", _("Thursday")), ("fri", _("Friday")), ("sat", _("Saturday")), ("sun", _("Sunday"))])
		self.timerentry_day = ConfigSubList()
		for x in (0, 1, 2, 3, 4, 5, 6):
			self.timerentry_day.append(ConfigYesNo(default = day[x]))
		servicename = self.timer.servicename
		self.timerentry_service = ConfigSelection([servicename])

	def createSetup(self, widget):
		self.list = []
		self.list.append(getConfigListEntry(_("Name"), self.timerentry_name))
		self.list.append(getConfigListEntry(_("Description"), self.timerentry_description))
		self.timerJustplayEntry = getConfigListEntry(_("Timer Type"), self.timerentry_justplay)
		self.list.append(self.timerJustplayEntry)
		self.entryDate = getConfigListEntry(_("Date"), self.timerentry_date)
		self.list.append(self.entryDate)
		self.entryStartTime = getConfigListEntry(_("StartTime"), self.timerentry_starttime)
		self.list.append(self.entryStartTime)
		self.entryShowEndTime = getConfigListEntry(_("Set End Time"), self.timerentry_showendtime)
		if self.timerentry_justplay.value == "1":
			self.list.append(self.entryShowEndTime)
		self.entryEndTime = getConfigListEntry(_("EndTime"), self.timerentry_endtime)	
		if self.timerentry_justplay.value != "1" or self.timerentry_showendtime.value:
			self.list.append(self.entryEndTime)			
		else:
			self.entryEndTime = None
		self.channelEntry = getConfigListEntry(_("Channel"), self.timerentry_service)
		self.list.append(self.channelEntry)
		self.dirname = getConfigListEntry(_("Location"), self.timerentry_dirname)
		if int(self.timerentry_justplay.value) != 1:
			self.list.append(self.dirname)
			self.list.append(getConfigListEntry(_("After event"), self.timerentry_afterevent))
		self[widget].list = self.list
		self[widget].l.setList(self.list)
		
	def newConfig(self):
		if self["config"].getCurrent() in (self.timerJustplayEntry, self.entryShowEndTime):
			self.createSetup("config")
			
	def keyLeft(self):
		if self["config"].getCurrent() == self.channelEntry and self.partnerboxentry is not None:
			from plugin import PartnerBouquetList
			self.session.openWithCallback(boundFunction(PartnerBouquetListCallback,self), PartnerBouquetList, [], self.partnerboxentry, 0, 0)
		elif self["config"].getCurrent() == self.timerentry_name:
			pass
		else:
			ConfigListScreen.keyLeft(self)
			self.newConfig()

	def keyRight(self):
		if self["config"].getCurrent() == self.channelEntry and self.partnerboxentry is not None:
			from plugin import PartnerBouquetList
			self.session.openWithCallback(boundFunction(PartnerBouquetListCallback,self), PartnerBouquetList, [], self.partnerboxentry, 0, 0)
		else:	
			ConfigListScreen.keyRight(self)
			self.newConfig()
		
	def getTimestamp(self, date, mytime):
		d = localtime(date)
		dt = datetime(d.tm_year, d.tm_mon, d.tm_mday, mytime[0], mytime[1])
		return int(mktime(dt.timetuple()))

	def getBeginEnd(self):
		date = self.timerentry_date.value
		endtime = self.timerentry_endtime.value
		starttime = self.timerentry_starttime.value
		begin = self.getTimestamp(date, starttime)
		end = self.getTimestamp(date, endtime)
		if end < begin:
			end += 86400
		return begin, end

	def keyCancel(self):
		self.close((False,))
		
	def keyGo(self):
		self.timer.name = self.timerentry_name.value
		self.timer.dirname = self.timerentry_dirname.value
		self.timer.afterEvent = {
		"nothing": 0,
		"deepstandby": 2,
		"standby": 1,
		"auto": 3
		}[self.timerentry_afterevent.value]
		self.timer.description = self.timerentry_description.value
		self.timer.justplay = int(self.timerentry_justplay.value)
		self.timer.timebegin, self.timer.timeend = self.getBeginEnd()
		self.close((True, self.timer))

	def incrementStart(self):
		self.timerentry_starttime.increment()
		self["config"].invalidate(self.entryStartTime)

	def decrementStart(self):
		self.timerentry_starttime.decrement()
		self["config"].invalidate(self.entryStartTime)

	def incrementEnd(self):
		if self.entryEndTime is not None:
			self.timerentry_endtime.increment()
			self["config"].invalidate(self.entryEndTime)

	def decrementEnd(self):
		if self.entryEndTime is not None:
			self.timerentry_endtime.decrement()
			self["config"].invalidate(self.entryEndTime)
	
# ##########################################
# TimerEntry
# ##########################################
baseTimerEntrySetup = None
baseTimerEntryGo = None
baseTimerEntrynewConfig = None
baseTimerkeyLeft = None
baseTimerkeyRight = None
baseTimerkeySelect = None
baseTimercreateConfig = None
baseTimer__init__ = None

def RemoteTimerInit():
	global baseTimerEntrySetup, baseTimerEntryGo, baseTimerEntrynewConfig, baseTimerkeyLeft, baseTimerkeyRight, baseTimerkeySelect, baseTimercreateConfig, baseTimer__init__
	if baseTimerEntrySetup is None:
		baseTimerEntrySetup = TimerEntry.createSetup
	if baseTimerEntryGo is None:
		baseTimerEntryGo = TimerEntry.keyGo
	if baseTimerEntrynewConfig is None:
		baseTimerEntrynewConfig = TimerEntry.newConfig
	if baseTimerkeyLeft is None:
		baseTimerkeyLeft = TimerEntry.keyLeft
	if baseTimerkeyRight is None:
		baseTimerkeyRight = TimerEntry.keyRight
	if baseTimerkeySelect is None:
		baseTimerkeySelect = TimerEntry.keySelect
	if baseTimercreateConfig is None:
		baseTimercreateConfig  = TimerEntry.createConfig
	if baseTimer__init__ is None:
		baseTimer__init__ = TimerEntry.__init__
	
	TimerEntry.createConfig = RemoteTimerConfig
	TimerEntry.keyLeft = RemoteTimerkeyLeft 
	TimerEntry.keyRight = RemoteTimerkeyRight
	TimerEntry.keySelect = RemoteTimerkeySelect
	TimerEntry.createSetup = createRemoteTimerSetup
	TimerEntry.keyGo = RemoteTimerGo
	TimerEntry.newConfig = RemoteTimernewConfig
	TimerEntry.__init__ = RemoteTimer__init__

def RemoteTimer__init__(self, session, timer):
	baseTimer__init__(self, session, timer)
	if int(self.timerentry_remote.value) != 0:
		RemoteTimernewConfig(self)
	
def RemoteTimerConfig(self):
	self.Locations = []
	self.entryguilist = []
	self.entryguilist.append(("0",_("No"),None))
	index = 1
	for c in config.plugins.Partnerbox.Entries:
		self.entryguilist.append((str(index),str(c.name.value),c))
		index = index + 1
	if config.plugins.Partnerbox.enabledefaultpartnerboxintimeredit.value and index > 1:
		default = "1"
	else:
		default = "0"
	self.timerentry_remote = ConfigSelection(default = default, choices = self.entryguilist)
	baseTimercreateConfig(self)

#def getLocationsError(self, error):
#	RemoteTimercreateConfig(self)
#	RemoteTimerCreateSetup(self,"config")

def getLocations(self, url, partnerboxentry, check, mode="new"):
	try:
		self.partnerboxentry = partnerboxentry
		sendPartnerBoxWebCommand(url, 3, "root", self.partnerboxentry.password.value, self.partnerboxentry.webinterfacetype.value).addCallback(boundFunction(getLocationsCallback,self, check = check, mode = mode)).addErrback(boundFunction(getLocationsCallbackError,self))
	except Exception, e:
		print e

def getLocationsCallbackError(self, error):
	msg = self.session.open(MessageBox, error.getErrorMessage(), MessageBox.TYPE_ERROR)
	msg.setTitle(_("Partnerbox"))
		
def getLocationsCallback(self, xmlstring, check = False, mode = "new"):
	try: root = xml.etree.cElementTree.fromstring(xmlstring)
	except: return 
	for location in root.findall("e2location"):
		add = True
		if check:
			add = location.text.encode("utf-8", 'ignore') not in self.Locations
		if add:
			self.Locations.append(location.text.encode("utf-8", 'ignore'))
	for location in root.findall("e2simplexmlitem"):  # vorerst Kompatibilitaet zum alten Webinterface-Api aufrecht erhalten (e2simplexmlitem)
		add = True
		if check:
			add = location.text.encode("utf-8", 'ignore') not in self.Locations
		if add:
			self.Locations.append(location.text.encode("utf-8", 'ignore'))
		
	# new as everything is async now	
	if len(self.Locations) == 0:
		ip = "%d.%d.%d.%d" % tuple(self.partnerboxentry.ip.value)
		port = self.partnerboxentry.port.value
		http_ = "%s:%d" % (ip,port)
		
		getLocations(self, "http://" + http_ + "/web/getcurrlocation", self.partnerboxentry, True)
	else:
		if mode == "new":
			RemoteTimercreateConfig(self)
			RemoteTimerCreateSetup(self,"config")
		else:
			from plugin import RemoteTimerList
			RemoteTimerList.openEditCallback(self)
		
def createRemoteTimerSetup(self, widget):
	baseTimerEntrySetup(self, widget)
	self.display = _("Remote Timer")
	self.timerRemoteEntry = getConfigListEntry(self.display, self.timerentry_remote)
	self.list.insert(0, self.timerRemoteEntry)
	self[widget].list = self.list
	
def RemoteTimerkeyLeft(self):
	if int(self.timerentry_remote.value) != 0:
		if self["config"].getCurrent() == self.channelEntry:
			from plugin import PartnerBouquetList
			self.session.openWithCallback(boundFunction(PartnerBouquetListCallback,self), PartnerBouquetList, [], self.entryguilist[int(self.timerentry_remote.value)][2], 0, 0)
		else:
			ConfigListScreen.keyLeft(self)
			RemoteTimernewConfig(self)
	else:
		baseTimerkeyLeft(self)

def RemoteTimerkeyRight(self):
	if int(self.timerentry_remote.value) != 0:
		if self["config"].getCurrent() == self.channelEntry:
			from plugin import PartnerBouquetList
			self.session.openWithCallback(boundFunction(PartnerBouquetListCallback,self), PartnerBouquetList, [], self.entryguilist[int(self.timerentry_remote.value)][2], 0, 0)
		else:
			ConfigListScreen.keyRight(self)
			RemoteTimernewConfig(self)
	else:
		baseTimerkeyRight(self)

def RemoteTimerkeySelect(self):
	if int(self.timerentry_remote.value) != 0:
		RemoteTimerGo(self)
	else:
		baseTimerkeySelect(self)
	
def RemoteTimernewConfig(self):
	if self["config"].getCurrent() == self.timerRemoteEntry:
		if int(self.timerentry_remote.value) != 0:
			ip = "%d.%d.%d.%d" % tuple(self.entryguilist[int(self.timerentry_remote.value)][2].ip.value)
			port = self.entryguilist[int(self.timerentry_remote.value)][2].port.value
			http_ = "%s:%d" % (ip,port)
			self.Locations = []
			getLocations(self, "http://" + http_ + "/web/getlocations", self.entryguilist[int(self.timerentry_remote.value)][2], False)
		else:
			baseTimercreateConfig(self)
			createRemoteTimerSetup(self, "config")
	elif self["config"].getCurrent() == self.timerJustplayEntry:
		if int(self.timerentry_remote.value) != 0:
			RemoteTimerCreateSetup(self,"config")
		else:
			baseTimerEntrynewConfig(self)
	else:
			if int(self.timerentry_remote.value) == 0:
				baseTimerEntrynewConfig(self)
	
def RemoteTimercreateConfig(self):
	justplay = self.timer.justplay
	afterevent = {
		AFTEREVENT.NONE: "nothing",
		AFTEREVENT.DEEPSTANDBY: "deepstandby",
		 AFTEREVENT.STANDBY: "standby",
		 AFTEREVENT.AUTO: "auto"
		}[self.timer.afterEvent]
	weekday_table = ("mon", "tue", "wed", "thu", "fri", "sat", "sun")
	day = []
	weekday = 0
	for x in (0, 1, 2, 3, 4, 5, 6):
		day.append(0)
	begin = self.timer.begin
	end = self.timer.end
	weekday = (int(strftime("%w", localtime(begin))) - 1) % 7
	day[weekday] = 1

	event = None
	if self.timer.eit:
		event =  eEPGCache.getInstance().lookupEventId(self.timer.service_ref.ref, self.timer.eit)

	if self.timer.name != "":
		name = self.timer.name 
	elif event is not None:
		name = event.getEventName()		
	else:
		name = ""
	if self.timer.description != "":
		description = self.timer.description
	elif event is not None:
		description = event.getShortDescription()
	else:
		description = ""
	self.timerentry_justplay = ConfigSelection(choices = [("zap", _("zap")), ("record", _("record"))], default = {0: "record", 1: "zap"}[justplay])
	self.timerentry_afterevent = ConfigSelection(choices = [("nothing", _("do nothing")), ("standby", _("go to standby")), ("deepstandby", _("go to deep standby")), ("auto", _("auto"))], default = afterevent)
	self.timerentry_name = ConfigText(default = name, visible_width = 50, fixed_size = False)
	self.timerentry_description = ConfigText(default = description, visible_width = 50, fixed_size = False)
	self.timerentry_date = ConfigDateTime(default = begin, formatstring = _("%d.%B %Y"), increment = 86400)
	self.timerentry_starttime = ConfigClock(default = begin)
	self.timerentry_endtime = ConfigClock(default = end)
	self.timerentry_showendtime = ConfigSelection(default = ((self.timer.end - self.timer.begin) > 4), choices = [(True, _("yes")), (False, _("no"))])	

	if self.Locations:
		default = self.Locations[0]
	else:
		default = "N/A"
	if default not in self.Locations:
		self.Locations.append(default)
	self.timerentry_dirname = ConfigSelection(default = default, choices = self.Locations)
	self.timerentry_weekday = ConfigSelection(default = weekday_table[weekday], choices = [("mon",_("Monday")), ("tue", _("Tuesday")), ("wed",_("Wednesday")), ("thu", _("Thursday")), ("fri", _("Friday")), ("sat", _("Saturday")), ("sun", _("Sunday"))])
	self.timerentry_day = ConfigSubList()
	for x in (0, 1, 2, 3, 4, 5, 6):
		self.timerentry_day.append(ConfigYesNo(default = day[x]))
	# FIXME some service-chooser needed here
	servicename = "N/A"
	try: # no current service available?
		servicename = str(self.timer.service_ref.getServiceName())
	except:
		pass
	self.timerentry_service_ref = self.timer.service_ref
	self.timerentry_service = ConfigSelection([servicename])

def RemoteTimerCreateSetup(self, widget):
	self.list = []
	self.timerRemoteEntry = getConfigListEntry(self.display, self.timerentry_remote)
	self.list.append(self.timerRemoteEntry)
	self.list.append(getConfigListEntry(_("Name"), self.timerentry_name))
	self.list.append(getConfigListEntry(_("Description"), self.timerentry_description))
	self.timerJustplayEntry = getConfigListEntry(_("Timer Type"), self.timerentry_justplay)
	self.list.append(self.timerJustplayEntry)
	self.entryDate = getConfigListEntry(_("Date"), self.timerentry_date)
	self.list.append(self.entryDate)
	self.entryStartTime = getConfigListEntry(_("StartTime"), self.timerentry_starttime)
	self.list.append(self.entryStartTime)
	
	self.entryShowEndTime = getConfigListEntry(_("Set End Time"), self.timerentry_showendtime)	
	if self.timerentry_justplay.value == "zap":
		self.list.append(self.entryShowEndTime)
	self.entryEndTime = getConfigListEntry(_("EndTime"), self.timerentry_endtime)
	if self.timerentry_justplay.value != "zap" or self.timerentry_showendtime.value:
		self.list.append(self.entryEndTime)
	else:
		self.entryEndTime = None
	self.channelEntry = getConfigListEntry(_("Channel"), self.timerentry_service)
	self.list.append(self.channelEntry)
	self.dirname = getConfigListEntry(_("Location"), self.timerentry_dirname)
	if self.timerentry_justplay.value != "zap":
		self.list.append(self.dirname)
		self.list.append(getConfigListEntry(_("After event"), self.timerentry_afterevent))
	self[widget].list = self.list
		
	self[widget].l.setList(self.list)

def PartnerBouquetListCallback(self, result):
	if result and result[1] and len(result[1])>0:
		self.timerentry_service_ref =  ServiceReference(result[1][0].servicereference)
		self.timerentry_service.setCurrentText(result[1][0].servicename)
		self.timerentry_name.value = result[1][0].eventtitle
		self.timerentry_description.value = result[1][0].eventdescription
		self.timerentry_date.value = result[1][0].eventstart
		t = localtime(result[1][0].eventstart)
		self.timerentry_starttime.value = [t.tm_hour, t.tm_min]
		t = localtime(result[1][0].eventstart+result[1][0].eventduration)
		self.timerentry_endtime.value = [t.tm_hour, t.tm_min]
		self["config"].invalidate(self.channelEntry)
		
def RemoteTimerGo(self):
	if int(self.timerentry_remote.value) == 0:
		baseTimerEntryGo(self)
	else:
		service_ref = self.timerentry_service_ref
		descr = self.timerentry_description.value
		begin, end = self.getBeginEnd()
		ip = "%d.%d.%d.%d" % tuple(self.entryguilist[int(self.timerentry_remote.value)][2].ip.value)
		port = self.entryguilist[int(self.timerentry_remote.value)][2].port.value
		http = "http://%s:%d" % (ip,port)

		name = self.timerentry_name.value
		self.timer.tags = self.timerentry_tags
		if self.timerentry_justplay.value == "zap":
			justplay = 1
			dirname = ""
		else:
			justplay = 0
			dirname = self.timerentry_dirname.value
		if dirname == "N/A":
			self.session.open(MessageBox,_("Timer can not be added...no locations on partnerbox available."),MessageBox.TYPE_INFO)
		else:
			afterevent = {
			"deepstandby": AFTEREVENT.DEEPSTANDBY,
			"standby": AFTEREVENT.STANDBY,
			}.get(self.timerentry_afterevent.value, AFTEREVENT.NONE)
			if service_ref.getPath(): # partnerbox service ?
				service_ref = getServiceRef(service_ref.ref.toString())

			sCommand = "%s/web/timeradd?sRef=%s&begin=%d&end=%d&name=%s&description=%s&dirname=%s&eit=0&justplay=%d&afterevent=%s" % (http, service_ref,begin,end,urllib.quote(name),urllib.quote(descr),urllib.quote(dirname),justplay,afterevent)
			sendPartnerBoxWebCommand(sCommand, 3, "root", str(self.entryguilist[int(self.timerentry_remote.value)][2].password.value), self.entryguilist[int(self.timerentry_remote.value)][2].webinterfacetype.value).addCallback(boundFunction(AddTimerE2Callback,self, self.session)).addErrback(boundFunction(AddTimerError,self,self.session))

def AddTimerE2Callback(self, session, answer):
	text = ""
	try: root = xml.etree.cElementTree.fromstring(answer)
	except: pass
	statetext = root.findtext("e2statetext")
	state = root.findtext("e2state")
	if statetext:
		text =  statetext.encode("utf-8", 'ignore')
	ok = state == "True"
	session.open(MessageBox,_("Partnerbox Answer: \n%s") % (text),MessageBox.TYPE_INFO, timeout = 10)
	if ok:
		if (config.plugins.Partnerbox.enablepartnerboxepglist.value): 
			# Timerlist der Partnerbox neu laden --> Anzeige fuer EPGList, aber nur, wenn die gleiche IP in EPGList auch angezeigt wird
			if partnerboxfunctions.CurrentIP == self.entryguilist[int(self.timerentry_remote.value)][2].ip.value:
				SetPartnerboxTimerlist(self.entryguilist[int(self.timerentry_remote.value)][2])
		self.keyCancel()

def AddTimerError(self, session, error):
	session.open(MessageBox,str(error.getErrorMessage()),MessageBox.TYPE_INFO)
	
		
		




