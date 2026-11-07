#
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
import Screens.ChannelSelection
from ServiceReference import ServiceReference
from Components.config import config, ConfigSelection, ConfigText, ConfigSubList, ConfigDateTime, ConfigClock, ConfigYesNo, getConfigListEntry
from Components.ActionMap import NumberActionMap, ActionMap
from Components.ConfigList import ConfigListScreen
from Components.SelectionList import SelectionList, SelectionEntryComponent
from Components.Label import Label
from Components.Pixmap import Pixmap
from RecordTimer import AFTEREVENT
from enigma import eEPGCache, getDesktop
from time import localtime, mktime, strftime
from datetime import datetime
from Screens.TimerEntry import TimerEntry
from Screens.MessageBox import MessageBox
from Screens.MovieSelection import getPreferredTagEditor
from Tools.BoundFunction import boundFunction
import urllib

import xml.etree.cElementTree

from PartnerboxFunctions import sendPartnerBoxWebCommand, getServiceRef, SetPartnerboxTimerlist, getBaseUrl
import PartnerboxFunctions as partnerboxfunctions
from time import localtime

sz_w = getDesktop(0).size().width()

class RemoteTagSelection(Screen):
	skin = """
		<screen name="RemoteTagSelection" position="center,center" size="600,450" title="Remote tags">
			<widget name="list" position="10,10" size="580,380" scrollbarMode="showOnDemand" />
			<widget name="key_green" position="10,400" size="200,40" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" />
		</screen>"""

	def __init__(self, session, available, selected):
		Screen.__init__(self, session)
		tags = list(available)
		for t in selected:
			if t not in tags:
				tags.append(t)
		tags.sort()
		self["list"] = SelectionList([SelectionEntryComponent(t, t, i, t in selected) for i, t in enumerate(tags)])
		self["key_green"] = Label(_("Save"))
		self["actions"] = ActionMap(["OkCancelActions", "ColorActions"], {
			"ok": self["list"].toggleSelection,
			"green": self.keySave,
			"cancel": self.close,
		}, -1)

	def keySave(self):
		self.close([x[1] for x in self["list"].getSelectionsList()])

class RemoteTimerEntry(TimerEntry):
	if sz_w == 1920:
		skin = """
        <screen name="RemoteTimerEntry" position="center,170" size="1200,820" title="Remote timer entry">
        <widget name="cancel" pixmap="Default-FHD/skin_default/buttons/red.svg" position="10,5" size="300,70" />
        <widget name="ok" pixmap="Default-FHD/skin_default/buttons/green.svg" position="310,5" size="300,70" />
        <widget backgroundColor="#9f1313" font="Regular;30" halign="center" name="canceltext" position="10,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
        <widget backgroundColor="#1f771f" font="Regular;30" halign="center" name="oktext" position="310,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="300,70" transparent="1" valign="center" zPosition="1" />
        <widget font="Regular;34" halign="right" position="1050,25" render="Label" size="120,40" source="global.CurrentTime">
            <convert type="ClockToText">Default</convert>
        </widget>
        <widget font="Regular;34" halign="right" position="800,25" render="Label" size="240,40" source="global.CurrentTime">
            <convert type="ClockToText">Date</convert>
        </widget>
        <eLabel backgroundColor="grey" position="10,80" size="1180,1" />
        <widget enableWrapAround="1" name="config" position="10,90" scrollbarMode="showOnDemand" size="1180,720" />
		</screen>"""
	else:
		skin = """
			<screen name="RemoteTimerEntry" position="center,center" size="820,420" title="Remote timer entry">
				<widget name="cancel" pixmap="skin_default/buttons/red.png" position="10,5" size="200,40" />
				<widget name="ok" pixmap="skin_default/buttons/green.png" position="210,5" size="200,40" />
				<widget name="canceltext" position="10,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#9f1313" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
				<widget name="oktext" position="210,5" size="200,40" zPosition="1" font="Regular;20" halign="center" valign="center" backgroundColor="#1f771f" transparent="1" shadowColor="black" shadowOffset="-2,-2" />
				<eLabel position="10,50" size="800,1" backgroundColor="grey" />
				<widget name="config" position="10,60" size="800,330" enableWrapAround="1" scrollbarMode="showOnDemand" />
			</screen>"""
		
	def __init__(self, session, timer, Locations, partnerboxentry = None, E2TimerList = [], mode="add"):
		self.partnerboxentry = partnerboxentry
		self.E2TimerList = E2TimerList
		self.mode = mode
		
		if self.mode == "edit":
			self.timeBeginOld = timer.timebegin
			self.timeEndOld = timer.timeend
			self.srefOld = timer.servicereference
		self.eit = timer.eit
		
		TimerEntry.__init__(self, session, timer)
		
		justplay = self.timer.justplay
		afterevent = {
			0: "nothing",
			2: "deepstandby",
			1: "standby",
			3: "auto"
			}[self.timer.afterEvent]
		
		default = self.timer.dirname
		if isUnsetDirname(default):
			default = getattr(self, "defaultLocation", None)
			if not default:
				default = self.Locations and self.Locations[0] or "N/A"
			self.timer.dirname = default
		if default not in self.Locations:
			self.Locations.append(default)	

		self.onLayoutFinish.append(self.setWindowTitle)	
	
	def setWindowTitle(self):
		if self.partnerboxentry is not None:
			self.setTitle("Remote timer entry %s" %(self.partnerboxentry.name.value))
	
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
	currentPartnerboxIndex = 0
	for c in config.plugins.Partnerbox.Entries:
		self.entryguilist.append((str(index),str(c.name.value),c))
		#HACK: self.partnerboxentry only exists when coming from remote timer list
		try:
			if c.name.value == self.partnerboxentry.name.value:
				currentPartnerboxIndex = index
		except:
			pass
		index = index + 1

	if currentPartnerboxIndex == 0:
		if config.plugins.Partnerbox.enabledefaultpartnerboxintimeredit.value and index > 1:
			default = "1"
		else:
			default = "0"
	else:
		default = str(currentPartnerboxIndex)
	self.timerentry_remote = ConfigSelection(default = default, choices = self.entryguilist)
	baseTimercreateConfig(self)

#def getLocationsError(self, error):
#	RemoteTimercreateConfig(self)
#	RemoteTimerCreateSetup(self,"config")

def getLocations(self, url, partnerboxentry, check, mode="new"):
	try:
		self.partnerboxentry = partnerboxentry
		self.defaultLocation = None
		sendPartnerBoxWebCommand(url, 3, "root", self.partnerboxentry.password.value, self.partnerboxentry.webinterfacetype.value).addCallback(boundFunction(getLocationsCallback,self, check = check, mode = mode)).addErrback(boundFunction(getLocationsCallbackError,self))
	except Exception, e:
		print e

def getLocationsCallbackError(self, error):
	msg = self.session.open(MessageBox, error.getErrorMessage(), MessageBox.TYPE_ERROR)
	msg.setTitle(_("Partnerbox"))
		
def getLocationsCallback(self, xmlstring, check = False, mode = "new"):
	# initialise self.Locations as it is for any unknown reason populated with the value None
	self.Locations = []
	try:
		root = xml.etree.cElementTree.fromstring(xmlstring)
	except:
		root = None

	if root is not None:
		# e2simplexmlitem: compatibility with the old webinterface API
		for location in root.findall("e2location") + root.findall("e2simplexmlitem"):
			if location.text:
				loc = location.text.encode("utf-8", 'ignore')
				if loc not in self.Locations:
					self.Locations.append(loc)
	getDefaultLocation(self, self.partnerboxentry, mode)
		
def getDefaultLocation(self, partnerboxentry, mode):
	try:
		sCommand = "%s/web/getcurrlocation" % getBaseUrl(partnerboxentry)
		sendPartnerBoxWebCommand(sCommand, 3, "root", partnerboxentry.password.value, partnerboxentry.webinterfacetype.value).addCallbacks(
			boundFunction(getDefaultLocationCallback, self, mode), boundFunction(getDefaultLocationError, self, mode))
	except Exception, e:
		print e
		finishLocations(self, mode)

def getDefaultLocationCallback(self, mode, xmlstring):
	loc = None
	try:
		root = xml.etree.cElementTree.fromstring(xmlstring)
		loc = root.findtext("e2location") or root.findtext("e2simplexmlitem")
	except:
		pass
	if loc:
		loc = loc.encode("utf-8", "ignore")
		self.defaultLocation = loc
		if loc in self.Locations:
			self.Locations.remove(loc)
		self.Locations.insert(0, loc)	# default first, so Locations[0] is the default everywhere
	finishLocations(self, mode)

def getDefaultLocationError(self, mode, error):
	print "getDefaultLocationError", error.getErrorMessage()
	finishLocations(self, mode)	# continue with what getlocations returned

def finishLocations(self, mode):
	# step 3: the former tail of getLocationsCallback
	if mode == "new":
		RemoteTimercreateConfig(self)
		RemoteTimerCreateSetup(self, "config")
	elif mode == "read":
		from plugin import RemoteTimerList
		RemoteTimerList.addTimerCallback(self)
	else:
		from plugin import RemoteTimerList
		RemoteTimerList.openEditCallback(self)

def isUnsetDirname(dirname):
	return not dirname or dirname in ("None", "N/A")

def getTags(self, partnerboxentry = None):
	if partnerboxentry is None:
		return
	try:
		http = getBaseUrl(partnerboxentry)
		sCommand = "%s/web/gettags" %(http)
		sendPartnerBoxWebCommand(sCommand, 3, "root", partnerboxentry.password.value, partnerboxentry.webinterfacetype.value).addCallback(boundFunction(getTagsCallback,self)).addErrback(boundFunction(getTagsCallbackError,self))
	except Exception,e: print str(e)
	
def getTagsCallback(self, xmlstring):
	self.tags = []
	try:
		root = xml.etree.cElementTree.fromstring(xmlstring)
	except:
		return

	for tag in root.findall("e2tag"):
		self.tags.append(tag.text.encode('utf-8', 'ignore'))
		
def getTagsCallbackError(self, error):
	msg = self.session.open(MessageBox, error.getErrorMessage(), MessageBox.TYPE_ERROR)
	msg.setTitle(_("Partnerbox"))
		
def createRemoteTimerSetup(self, widget):
	baseTimerEntrySetup(self, widget)
	self.display = _("Remote Timer")
	self.timerRemoteEntry = getConfigListEntry(self.display, self.timerentry_remote)
	self.list.insert(0, self.timerRemoteEntry)
	self[widget].list = self.list
	
def RemoteTimerkeyLeft(self):
	if int(self.timerentry_remote.value) != 0:
		cur = self["config"].getCurrent()
		if cur and cur == self.channelEntry:
			openPartnerBouquetList(self)
		elif cur and cur == self.tagsSet:
			openRemoteTagSelection(self)
		else:
			ConfigListScreen.keyLeft(self)
			RemoteTimernewConfig(self)
	else:
		baseTimerkeyLeft(self)

def RemoteTimerkeyRight(self):
	if int(self.timerentry_remote.value) != 0:
		cur = self["config"].getCurrent()
		if cur and cur == self.channelEntry:
			openPartnerBouquetList(self)
		elif cur and cur == self.tagsSet:
			openRemoteTagSelection(self)
		else:
			ConfigListScreen.keyRight(self)
			RemoteTimernewConfig(self)
	else:
		baseTimerkeyRight(self)

def RemoteTimerkeySelect(self):
	if int(self.timerentry_remote.value) != 0:
		cur = self["config"].getCurrent()
		if cur and cur == self.channelEntry:
			openPartnerBouquetList(self)
		elif cur and cur == self.tagsSet:
			openRemoteTagSelection(self)
		else:
			RemoteTimerGo(self)
	else:
		baseTimerkeySelect(self)

def openPartnerBouquetList(self):
	try:
		timerlist = self.E2TimerList
	except:
		timerlist = []
	from plugin import PartnerboxBouquetList
	self.session.openWithCallback(boundFunction(self.PartnerBouquetListCallback), PartnerboxBouquetList, self.entryguilist[int(self.timerentry_remote.value)][2], 0, 0)

def openRemoteTagSelection(self):
	available = getattr(self, "tags", None)
	if available is None:
		self.session.open(MessageBox, _("Tags are still being loaded from the partnerbox."), MessageBox.TYPE_INFO, timeout=5)
		return
	self.session.openWithCallback(boundFunction(RemoteTagSelectionCallback, self), RemoteTagSelection, available, self.timerentry_tags)	

def RemoteTagSelectionCallback(self, ret):
	if ret is None:
		return
	self.timerentry_tags = ret
	self.timerentry_tagsset.setChoices([ret and " ".join(ret) or "None"])
	self["config"].invalidate(self.tagsSet)

def RemoteTimernewConfig(self):
	if self["config"].getCurrent() == self.timerRemoteEntry:
		if int(self.timerentry_remote.value) != 0:
			http = getBaseUrl(self.entryguilist[int(self.timerentry_remote.value)][2])
			self.Locations = []
			getLocations(self, http + "/web/getlocations", self.entryguilist[int(self.timerentry_remote.value)][2], False)
			self.tags = []
			getTags(self, self.entryguilist[int(self.timerentry_remote.value)][2])
		else:
			baseTimercreateConfig(self)
			createRemoteTimerSetup(self, "config")
	elif self["config"].getCurrent() in (self.timerTypeEntry, self.timerJustplayEntry, self.frequencyEntry, self.entryShowEndTime):
		if int(self.timerentry_remote.value) != 0:
			RemoteTimerCreateSetup(self,"config")
		else:
			baseTimerEntrynewConfig(self)
	elif getPreferredTagEditor() and self["config"].getCurrent() == self.tagsSet:
		self.session.openWithCallback(
			self.tagEditFinished,
			getPreferredTagEditor(),
			self.timerentry_tags
		)					
					
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
	if self.timer.repeated:
		type = "repeated"
		if (self.timer.repeated == 31): # Mon-Fri
			repeated = "weekdays"
		elif (self.timer.repeated == 127): # daily
			repeated = "daily"
		else:
			flags = self.timer.repeated
			repeated = "user"
			count = 0
			for x in (0, 1, 2, 3, 4, 5, 6):
				if flags == 1: # weekly
					print "Set to weekday " + str(x)
					weekday = x
				if flags & 1 == 1: # set user defined flags
					day[x] = 1
					count += 1
				else:
					day[x] = 0
				flags = flags >> 1
			if count == 1:
				repeated = "weekly"
	else: # once
		type = "once"
		repeated = None
		weekday = (int(strftime("%w", localtime(self.timer.begin))) - 1) % 7
		day[weekday] = 1
	begin = self.timer.begin
	end = self.timer.end

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
	self.timerentry_justplay = ConfigSelection(choices = [("1", _("zap")), ("0", _("record"))], default = {0: "0", 1: "1"}[justplay])

	self.timerentry_type = ConfigSelection(choices = [("once", _("once")), ("repeated", _("repeated"))], default = type)
	
	self.timerentry_afterevent = ConfigSelection(choices = [("nothing", _("do nothing")), ("standby", _("go to standby")), ("deepstandby", _("go to deep standby")), ("auto", _("auto"))], default = afterevent)
	self.timerentry_name = ConfigText(default = name, visible_width = 50, fixed_size = False)
	self.timerentry_description = ConfigText(default = description, visible_width = 50, fixed_size = False)
	self.timerentry_tags = self.timer.tags[:]
	self.timerentry_tagsset = ConfigSelection(choices = [not self.timerentry_tags and "None" or " ".join(self.timerentry_tags)])
	self.timerentry_repeated = ConfigSelection(default = repeated, choices = [("daily", _("daily")), ("weekly", _("weekly")), ("weekdays", _("Mon-Fri")), ("user", _("user defined"))])
	self.timerentry_date = ConfigDateTime(default = begin, formatstring = _("%d.%B %Y"), increment = 86400)
	self.timerentry_starttime = ConfigClock(default = begin)
	self.timerentry_endtime = ConfigClock(default = end)
	self.timerentry_showendtime = ConfigSelection(default = ((self.timer.end - self.timer.begin) > 4), choices = [(True, _("yes")), (False, _("no"))])	

	default = self.timer.dirname
	if isUnsetDirname(default):
		default = getattr(self, "defaultLocation", None)
		if not default:
			default = self.Locations and self.Locations[0] or "N/A"
		self.timer.dirname = default
	if default not in self.Locations:
		self.Locations.append(default)
	self.timerentry_dirname = ConfigSelection(default = default, choices = self.Locations)

	repeatedbegin = begin
	if self.timer.repeatedbegindate > 0:
		repeatedbegin = self.timer.repeatedbegindate
	
	self.timerentry_repeatedbegindate = ConfigDateTime(default = repeatedbegin, formatstring = _("%d.%B %Y"), increment = 86400)
	
	self.timerentry_weekday = ConfigSelection(default = weekday_table[weekday], choices = [("mon",_("Monday")), ("tue", _("Tuesday")), ("wed",_("Wednesday")), ("thu", _("Thursday")), ("fri", _("Friday")), ("sat", _("Saturday")), ("sun", _("Sunday"))])
	self.timerentry_day = ConfigSubList()
	for x in (0, 1, 2, 3, 4, 5, 6):
		self.timerentry_day.append(ConfigYesNo(default = day[x]))
	servicename = "N/A"
	try: # no current service available?
		servicename = str(self.timer.service_ref.getServiceName())
	except:
		pass
		
	if servicename == "":
		servicename = self.timer.servicename
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
	self.timerTypeEntry = getConfigListEntry(_("Repeat Type"), self.timerentry_type)
	self.list.append(self.timerTypeEntry)

	if self.timerentry_type.value == "once":
		self.frequencyEntry = None
	else: # repeated
		self.frequencyEntry = getConfigListEntry(_("Repeats"), self.timerentry_repeated)
		self.list.append(self.frequencyEntry)
		self.repeatedbegindateEntry = getConfigListEntry(_("Starting on"), self.timerentry_repeatedbegindate)
		self.list.append(self.repeatedbegindateEntry)
		if self.timerentry_repeated.value == "daily":
			pass
		if self.timerentry_repeated.value == "weekdays":
			pass
		if self.timerentry_repeated.value == "weekly":
			self.list.append(getConfigListEntry(_("Weekday"), self.timerentry_weekday))
		
		if self.timerentry_repeated.value == "user":
			self.list.append(getConfigListEntry(_("Monday"), self.timerentry_day[0]))
			self.list.append(getConfigListEntry(_("Tuesday"), self.timerentry_day[1]))
			self.list.append(getConfigListEntry(_("Wednesday"), self.timerentry_day[2]))
			self.list.append(getConfigListEntry(_("Thursday"), self.timerentry_day[3]))
			self.list.append(getConfigListEntry(_("Friday"), self.timerentry_day[4]))
			self.list.append(getConfigListEntry(_("Saturday"), self.timerentry_day[5]))
			self.list.append(getConfigListEntry(_("Sunday"), self.timerentry_day[6]))	
	
	self.entryDate = getConfigListEntry(_("Date"), self.timerentry_date)
	if self.timerentry_type.value == "once":
		self.list.append(self.entryDate)
	self.entryStartTime = getConfigListEntry(_("StartTime"), self.timerentry_starttime)
	self.list.append(self.entryStartTime)
	
	self.entryShowEndTime = getConfigListEntry(_("Set End Time"), self.timerentry_showendtime)

	if self.timerentry_justplay.value == "1": #zap
		self.list.append(self.entryShowEndTime)
	self.entryEndTime = getConfigListEntry(_("EndTime"), self.timerentry_endtime)
	if self.timerentry_justplay.value != "1" or self.timerentry_showendtime.value:
		self.list.append(self.entryEndTime)
	else:
		self.entryEndTime = None
	self.channelEntry = getConfigListEntry(_("Channel"), self.timerentry_service)
	self.list.append(self.channelEntry)
	self.dirname = getConfigListEntry(_("Location"), self.timerentry_dirname)
	self.tagsSet = getConfigListEntry(_("Tags"), self.timerentry_tagsset)

	if self.timerentry_justplay.value != "1": # zap
		if config.usage.setup_level.index >= 2: # expert+
			self.list.append(self.dirname)
		if getPreferredTagEditor():
			self.list.append(self.tagsSet)
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
		tags = urllib.quote(" ".join(self.timerentry_tags))
		if self.timerentry_justplay.value == "zap" or self.timerentry_justplay.value == "1":
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
			"auto": AFTEREVENT.AUTO,
			"nothing": AFTEREVENT.NONE
			}.get(self.timerentry_afterevent.value, AFTEREVENT.NONE)
			if service_ref.getPath(): # partnerbox service ?
				service_ref = getServiceRef(service_ref.ref.toString())

			self.timer.resetRepeated()
			if self.timerentry_type.value == "repeated":
				if self.timerentry_repeated.value == "daily":
					for x in (0, 1, 2, 3, 4, 5, 6):
						self.timer.setRepeated(x)
				
				elif self.timerentry_repeated.value == "weekly":
					self.timer.setRepeated(self.timerentry_weekday.index)

				elif self.timerentry_repeated.value == "weekdays":
					for x in (0, 1, 2, 3, 4):
						self.timer.setRepeated(x)

				elif self.timerentry_repeated.value == "user":
					for x in (0, 1, 2, 3, 4, 5, 6):
						if self.timerentry_day[x].value:
							self.timer.setRepeated(x)
						
			# this is an ugly hack. When a timer is created out of EPG self.mode does not exist. 
			try:
				self.mode
			except:
				self.mode = "add"
	
			if self.mode == "add":
				sCommand = "%s/web/timeradd?sRef=%s&begin=%d&end=%d&name=%s&description=%s&dirname=%s&tags=%s&eit=%s&justplay=%d&afterevent=%s&repeated=%d" % (http, service_ref,begin,end,urllib.quote(name),urllib.quote(descr),urllib.quote(dirname), tags, self.timer.eit, justplay,afterevent, self.timer.repeated)
			else: # edit
				sCommand = "%s/web/timerchange?sRef=%s&begin=%s&end=%s&name=%s&description=%s&dirname=%s&tags=%s&afterevent=%s&eit=%s&disabled=0&justplay=%s&repeated=%d&channelOld=%s&beginOld=%s&endOld=%s&deleteOldOnSave=1" % (http, service_ref, begin, end, urllib.quote(name), urllib.quote(descr), urllib.quote(dirname), tags, afterevent, self.eit, justplay, self.timer.repeated, self.srefOld, self.timeBeginOld, self.timeEndOld   )
			
			sendPartnerBoxWebCommand(sCommand, 3, "root", str(self.entryguilist[int(self.timerentry_remote.value)][2].password.value), self.entryguilist[int(self.timerentry_remote.value)][2].webinterfacetype.value).addCallback(boundFunction(AddTimerE2Callback,self, self.session)).addErrback(boundFunction(AddTimerError,self,self.session))
			

def AddTimerE2Callback(self, session, answer):
	text = ""
	try:
		root = xml.etree.cElementTree.fromstring(answer)
	except Exception:
		session.open(MessageBox, _("Partnerbox: invalid response"), MessageBox.TYPE_INFO, timeout=10)
		return
	statetext = root.findtext("e2statetext")
	state = root.findtext("e2state")
	if statetext:
		text =  statetext.encode("utf-8", 'ignore')
	ok = state == "True"
	session.open(MessageBox,_("Partnerbox Answer: \n%s") % (text),MessageBox.TYPE_INFO, timeout = 10)
	if ok:
		if self.mode == "edit":
				self.close((False, True))
		else:
			if (config.plugins.Partnerbox.enablepartnerboxepglist.value): 
			# Timerlist der Partnerbox neu laden --> Anzeige fuer EPGList, aber nur, wenn die gleiche IP in EPGList auch angezeigt wird
				if partnerboxfunctions.CurrentIP == self.entryguilist[int(self.timerentry_remote.value)][2].ip.value:
					SetPartnerboxTimerlist(self.entryguilist[int(self.timerentry_remote.value)][2])
			self.keyCancel()

def AddTimerError(self, session, error):
	session.open(MessageBox,str(error.getErrorMessage()),MessageBox.TYPE_INFO)
	
		
		




