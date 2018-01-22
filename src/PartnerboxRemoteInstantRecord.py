#
#  Partnerbox E2
#
#  $Id$
#
#  Coded by Dr.Best (c) 2009
#  RemoteTimerInstantRecord implemented by dre (c) 2018
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
from PartnerboxFunctions import sendPartnerBoxWebCommand
from PartnerboxSetup import PartnerboxEntriesListConfigScreen
from Screens.InfoBarGenerics import InfoBarInstantRecord
from Screens.MessageBox import MessageBox
from Tools.BoundFunction import boundFunction
import xml.etree.cElementTree
import urllib
from time import time
from RemoteTimerList import RemoteTimerList

baseInstantRecCallback = None
baseInstantRecording__init__ = None
baseInstantIsRecording = None

def RemoteInstantRecordingInit():
	global baseInstantRecording__init__, baseInstantRecord, baseInstantRecCallback, baseInstantIsRecording
	if baseInstantRecording__init__ is None:
		baseInstantRecording__init__ = InfoBarInstantRecord.__init__
	if baseInstantRecCallback is None:
		baseInstantRecCallback = InfoBarInstantRecord.recordQuestionCallback
	if baseInstantIsRecording is None:
		baseInstantIsRecording = InfoBarInstantRecord.isInstantRecordRunning
		
	InfoBarInstantRecord.__init__ = RemoteInstantRecord__init__
	InfoBarInstantRecord.recordQuestionCallback = RemoteInstantRecord_recordQuestionCallback
	InfoBarInstantRecord.isInstantRecordRunning = RemoteInstantRecord_isInstantRecordRunning
		
def RemoteInstantRecord__init__(self):
	# init InfoBarInstantRecord
	baseInstantRecording__init__(self)
	if config.plugins.Partnerbox.entriescount.value != 0:
		self.remoteRecordingRunning = False
		# add our own options required for remote instant recording
		temp_list = list(self.startOptionList)
		temp_list.insert(-1, (_("add recording on Partnerbox (stop after current event)"),"pb_event"))
		temp_list.insert(-1, (_("add recording on Partnerbox (indefinitely)"), "pb_indefinitely"))
		self.startOptionList = tuple(temp_list)
		temp_list = list(self.stopOptionList)
		temp_list.insert(-1, (_("stop recording on Partnerbox"), "pb_stop"))
		self.stopOptionList = tuple(temp_list)

def RemoteInstantRecord_recordQuestionCallback(self, answer):
	# record now records the current channel on Partnerbox not the current channel on client...
	if answer and answer[1] == "pb_event":
		print "[Partnerbox] - selected option is for Partnerbox - event"
		self.rectype = "current"
		if config.plugins.Partnerbox.entriescount.value == 1 or config.plugins.Partnerbox.enabledefaultpartnerboxintimeredit.value:
			getEPGNow(self, self.session, None, config.plugins.Partnerbox.Entries[0])
		else:
			self.session.openWithCallback(boundFunction(getEPGNow, self), PartnerboxEntriesListConfigScreen)
	elif answer and answer[1] == "pb_indefinitely":
		print "[Partnerbox] - selected option is for Partnerbox - indefinitely"
		self.rectype = "infinite"
		if config.plugins.Partnerbox.entriescount.value == 1 or config.plugins.Partnerbox.enabledefaultpartnerboxintimeredit.value:
			addInfiniteRemoteRecording(self, self.session, None, config.plugins.Partnerbox.Entries[0])
		else:
			self.session.openWithCallback(boundFunction(addInfiniteRemoteRecording, self), PartnerboxEntriesListConfigScreen)
	elif answer and answer[1] == "pb_stop":
		print "[Partnerbox] - selected option is for Partnerbox - stop"
		if config.plugins.Partnerbox.entriescount.value == 1 or config.plugins.Partnerbox.enabledefaultpartnerboxintimeredit.value:
			openRemoteTimerList(self, self.session, None, config.plugins.Partnerbox.Entries[0])
		else:
			self.session.openWithCallback(boundFunction(openRemoteTimerList, self), PartnerboxEntriesListConfigScreen)
	else:
		print "[Partnerbox] - selected option is not for Partnerbox. Use standard handling"
		baseInstantRecCallback(self, answer)

def addInfiniteRemoteRecording(self, session, what, partnerboxentry):
	if setPartnerboxData(self, self.session, None, partnerboxentry):
		self.sref = getServiceReference(self)
		if self.sref == "":
			self.session.open(MessageBox, _("This is not a Partnerbox channel"), MessageBox.TYPE_ERROR, timeout=5)
		else:
			begin = int(time())
			end = begin + 3600
			#todo: read insta rec dir
			name = urllib.quote(_("Instant Record"))
			dir = urllib.quote("/media/hdd/movie")
			url = "http://%s:%d/web/timeradd?sRef=%s&begin=%d&end=%d&name=%s&dirname=%s&eit=0&description=" %(self.ip, self.port, self.sref, begin, end, name, dir)
			sendPartnerBoxWebCommand(url).addCallback(boundFunction(RemoteInstantRecordCallback, self)).addErrback(boundFunction(RemoteInstantRecordError, self))	
	else:
		self.session.open(MessageBox, _("Partnerbox Serverbox does not support recording"), MessageBox.TYPE_ERROR, timeout=5)	

def getEPGNow(self, session, what, partnerboxentry):
	if setPartnerboxData(self, self.session, None, partnerboxentry):
		self.sref = getServiceReference(self)
		if self.sref == "":
			self.session.open(MessageBox, _("This is not a Partnerbox channel"), MessageBox.TYPE_ERROR, timeout=5)
		else:
			url = "http://%s:%d/web/epgservicenow?sRef=%s" %(self.ip, self.port, self.sref)
			sendPartnerBoxWebCommand(url, 5, "root", self.password, self.webiftype).addCallback(boundFunction(getEPGNowCallback, self)).addErrback(boundFunction(RemoteInstantRecordError, self))				
	else:
		self.session.open(MessageBox, _("Partnerbox Serverbox does not support recording"), MessageBox.TYPE_ERROR, timeout=5)	

def getEPGNowCallback(self, result):
	text = ""
	try:
		root = xml.etree.cElementTree.fromstring(result)
	except:
		pass
	
	event = root.find("e2event", None)
	if event is not None:
		eventid = event.findtext("e2eventid", None)
		if eventid is not None:
			# add a timer for the current event
			url = "http://%s:%d/web/timeraddbyeventid?sRef=%s&eventid=%s" %(self.ip, self.port, self.sref, eventid)
		else:
			begin = int(time())
			end = begin + 3600
			name = urllib.quote(_("Instant Record"))
			#todo: read insta rec dir		
			dir = urllib.quote("/media/hdd/movie")
			url = "http://%s:%d/web/timeradd?sRef=%s&begin=%d&end=%d&name=%s&dirname=/media/hdd/movie&eit=0" %(self.ip, self.port, self.sref, begin, end, name, dir)
	
		sendPartnerBoxWebCommand(url).addCallback(boundFunction(RemoteInstantRecordCallback, self)).addErrback(boundFunction(RemoteInstantRecordError, self))

def RemoteInstantRecordCallback(self, result):
	text = ""
	try:
		root = xml.etree.cElementTree.fromstring(result)
	except:
		pass
	statetext = root.findtext("e2statetext")
	state = root.findtext("e2state")
	if statetext:
		text = statetext.encode("utf-8", 'ignore')
	ok = state == "True"
	self.session.open(MessageBox, _("Partnerbox Answer: \n%s") %(text), MessageBox.TYPE_INFO, timeout=5)
	self.remoteRecordingRunning = True
	
def RemoteInstantRecordError(self, error):
	self.session.open(MessageBox, str(error.getErrorMessage()), MessageBox.TYPE_INFO)

def RemoteInstantRecord_isInstantRecordRunning(self):
	if self.remoteRecordingRunning:
		print "[Partnerbox] - Remote recording is running"
		return True
	else:
		return baseInstantIsRecording(self)

def openRemoteTimerList(self, session, what, partnerboxentry):
	self.session.openWithCallback(boundFunction(resetRecordingState, self), RemoteTimerList, partnerboxentry)
		
def resetRecordingState(self):
	self.remoteRecordingRunning = False
		
def getServiceReference(self):
	# get the currently running channel
	currentRef = self.session.nav.getCurrentlyPlayingServiceReference()
	# check whether the channel is a Partnerbox stream
	if currentRef.getPath():
		oldRef = currentRef.getPath()
		# get service reference for serverbox
		currentRef.setPath("")
		sref = currentRef.toString()
		currentRef.setPath(oldRef)
		# remove channel name
		pos = sref.find("::")
		sref = sref[:pos-1]
		return sref
	else:
		return ""

def setPartnerboxData(self, session, what, partnerboxentry):
	if partnerboxentry.canRecord.value:
		self.ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
		self.port = partnerboxentry.port.value
		self.password = partnerboxentry.password.value
		self.webiftype = partnerboxentry.webinterfacetype.value
		return True
	return False	