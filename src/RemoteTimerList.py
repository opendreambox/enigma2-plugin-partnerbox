#
#  Partnerbox E2
#
#  $Id$
#
#  Coded by Dr.Best (c) 2009
#  RemoteTimerList implemented by dre (c) 2017 - 2018
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

from Components.config import config
from Components.ActionMap import ActionMap
from Components.Pixmap import Pixmap
from Components.TimerList import TimerList
from Screens.MessageBox import MessageBox
from Screens.TimerEdit import TimerEditList
from PartnerboxFunctions import FillE2TimerList, sendPartnerBoxWebCommand
from PartnerboxSetup import PartnerboxEntriesListConfigScreen
from RemoteTimerEntry import RemoteTimerEntry
from ServiceReference import ServiceReference
from Tools.Directories import resolveFilename, SCOPE_CURRENT_SKIN
from Tools.FuzzyDate import FuzzyTime
from Tools.LoadPixmap import LoadPixmap
from enigma import eServiceReference, getDesktop
from timer import TimerEntry as RealTimerEntry
from timer import TimerEntry
import urllib

sz_w = getDesktop(0).size().width()

class RemoteTimerList(TimerEditList):
	if sz_w == 1920:
		skin = """
        <screen name="RemoteTimerList" position="center,170" size="1200,820" title="Remote Timer Editor">
        <ePixmap pixmap="Default-FHD/skin_default/buttons/red.svg" position="10,5" scale="stretch" size="270,70" />
        <ePixmap pixmap="Default-FHD/skin_default/buttons/green.svg" position="280,5" scale="stretch" size="270,70" />
        <ePixmap pixmap="Default-FHD/skin_default/buttons/yellow.svg" position="550,5" scale="stretch" size="270,70" />
        <ePixmap pixmap="Default-FHD/skin_default/buttons/blue.svg" position="820,5" scale="stretch" size="270,70" />
        <widget backgroundColor="#9f1313" font="Regular;30" halign="center" name="key_red" position="10,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="270,70" transparent="1" valign="center" zPosition="1" />
        <widget backgroundColor="#1f771f" font="Regular;30" halign="center" name="key_green" position="280,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="270,70" transparent="1" valign="center" zPosition="1" />
        <widget backgroundColor="#a08500" font="Regular;30" halign="center" name="key_yellow" position="550,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="270,70" transparent="1" valign="center" zPosition="1" />
        <widget backgroundColor="#18188b" font="Regular;30" halign="center" name="key_blue" position="820,5" foregroundColor="white" shadowColor="black" shadowOffset="-2,-2" size="270,70" transparent="1" valign="center" zPosition="1" />
        <eLabel backgroundColor="grey" position="10,80" size="1180,1" />
        <widget enableWrapAround="1" name="timerlist" position="10,90" scrollbarMode="showOnDemand" size="1180,700" />
        <ePixmap pixmap="Default-FHD/skin_default/icons/info.svg" position="1110,30" size="80,40" />
        <widget name="menubutton" pixmap="Default-FHD/skin_default/icons/menu.svg" position="1110,30" size="80,40" zPosition="1" />
		</screen>"""
	else:
		skin = """  <screen name="RemoteTimerList" position="center,120" size="950,520" title="Remote Timer Editor">
    		<ePixmap pixmap="skin_default/buttons/red.png" position="10,5" size="200,40" />
	    	<ePixmap pixmap="skin_default/buttons/green.png" position="210,5" size="200,40" />
	    	<ePixmap pixmap="skin_default/buttons/yellow.png" position="410,5" size="200,40" />
		    <ePixmap pixmap="skin_default/buttons/blue.png" position="610,5" size="200,40" />
	    	<widget name="menubutton" pixmap="skin_default/icons/menu.png" position="810,15" size="100,20"  />
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
		self._timerlist = TimerList(self.list)
		self["timerlist"] = self._timerlist
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

	def downloadError(self, error = None):
		if error is not None:
			self.session.open(MessageBox,str(error.getErrorMessage()),  MessageBox.TYPE_INFO)
			#TODO: if serverbox is down don't allow to add/remove/edit/... timer
			
	def readXML(self, xmlstring):
		self.E2TimerList = []
		self.E2TimerList = FillE2TimerList(xmlstring)

		#helper function to move finished timers to end of list
		def eol_compare(x, y):
			if x[0].state != y[0].state and x[0].state == RealTimerEntry.StateEnded or y[0].state == RealTimerEntry.StateEnded:
				return cmp(x[0].state, y[0].state)
			return cmp(x[0].begin, y[0].begin)
		
		timers = [(timer, False) for timer in self.E2TimerList if timer.state < 3]
		timers.extend([(timer, True) for timer in self.E2TimerList if timer.state == 3])
		
		if config.usage.timerlist_finished_timer_position.index: #end of list
			timers.sort(cmp = eol_compare)
		else:
			timers.sort(key = lambda x: x[0].begin)		
		
		self.list = timers
		self._timerlist.list = self.list
		self["timerlist"].instance.show()		
		self.updateState()
		
	def toggleDisabledState(self):
		t =  self["timerlist"].getCurrent()
		
		if t.disabled == 0:
			disabled = 1
		else:
			disabled = 0
			
		tagset = ""
		for tag in t.tags:
			if tag == 'None':
				break
			if tagset == "":
				tagset = tag
			else:
				tagset += " " + tag
				
		sCommand = "http://%s:%d/web/timerchange?sRef=%s&begin=%s&end=%s&name=%s&description=%s&dirname=%s&tags=%s&afterevent=%s&eit=%s&disabled=%s&justplay=%s&channelOld=%s&beginOld=%s&endOld=%s&repeated=%d&deleteOldOnSave=1" % (self.ip, self.port, t.servicereference, t.timebegin, t.timeend, urllib.quote(t.name), urllib.quote(t.description), urllib.quote(t.dirname), urllib.quote(tagset), t.afterEvent, t.eit, disabled, t.justplay, t.servicereference, t.timebegin, t.timeend, t.repeated  )
		
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
		from RemoteTimerEntry import getLocations
		
		self.Locations = []
		self.timer = timer
		
		ip = "%d.%d.%d.%d" % tuple(self.partnerboxentry.ip.value)
		port = self.partnerboxentry.port.value
		http_ = "%s:%d" % (ip,port)
		getLocations(self, "http://" + http_ + "/web/getlocations", self.partnerboxentry, False, "read")
		
	def addTimerCallback(self):
		from RemoteTimerEntry import RemoteTimerEntry
		
		self.session.openWithCallback(self.finishedAdd, RemoteTimerEntry, self.timer, self.Locations, self.partnerboxentry, self.E2TimerList)	
	
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
		self.session.openWithCallback(self.finishedEdit, RemoteTimerEntry, self.currentTimer, self.Locations, self.partnerboxentry, self.E2TimerList, mode="edit")
	
	def finishedEdit(self, answer):
		# when editing a timer from Remote Timer List the timer is already updated there. So, answer[0] is False
		if answer[0]:
			t = answer[1]
		
			tagset = ""
			for tag in t.tags:
				if tag == 'None':
					break
				if tagset == "":
					tagset = tag
				else:
					tagset += " " + tag			
			
			sCommand = "http://%s:%d/web/timerchange?sRef=%s&begin=%s&end=%s&name=%s&description=%s&dirname=%s&tags=%s&afterevent=%s&eit=%s&disabled=%s&justplay=%s&channelOld=%s&beginOld=%s&endOld=%s&repeated=%d&deleteOldOnSave=1" % (self.ip, self.port, t.servicereference, t.timebegin, t.timeend, urllib.quote(t.name), urllib.quote(t.description), urllib.quote(t.dirname), urllib.quote(tagset), t.afterEvent, t.eit, t.disabled, t.justplay, self.srefOld, self.timeBeginOld, self.timeEndOld, t.repeated   )			
		
			sendPartnerBoxWebCommand(sCommand, 10, self.username, self.password, self.webiftype).addCallback(self.timerChangeCallback).addErrback(self.actionError)
		else:
			# this is used when editing a timer from Remote Timer List. As the timer is already changed we only need to reload the list
			if len(answer)>1:
				if answer[1] == True:
					self.readRemoteTimers()
			else:
				print "Timeredit aborted"
	
	def cleanupTimer(self, delete):
		if delete:
			sCommand = "http://%s:%d/web/timercleanup?cleanup=true" % (self.ip, self.port)
			
			sendPartnerBoxWebCommand(sCommand, 10, self.username, self.password, self.webiftype).addCallback(self.timerChangeCallback).addErrback(self.actionError)
			
	def cleanupTimerCallback(self, result):
		self.readRemoteTimers()
