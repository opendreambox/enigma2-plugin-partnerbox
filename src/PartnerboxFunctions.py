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

from time import localtime
from timer import TimerEntry
import xml.etree.cElementTree
import urlparse
import connector as myconnector
from Tools.BoundFunction import boundFunction
from ServiceReference import ServiceReference

CurrentIP = None
remote_timer_list = None

def url_parse(url, defaultPort=None):
	parsed = urlparse.urlparse(url)
	scheme = parsed[0]
	path = urlparse.urlunparse(('', '') + parsed[2:])
	if defaultPort is None:
		if scheme == 'https':
			defaultPort = 443
		else:
			defaultPort = 80
	host, port = parsed[1], defaultPort
	if ':' in host:
		host, port = host.split(':')
		port = int(port)
	return scheme, host, port, path

def getTimerType(refstr, beginTime, duration, eit, timer_list):
	pre = 1
	post = 2
	type = 0
	endTime = beginTime + duration
	for x in timer_list:
		if x.servicereference.upper() == refstr.upper():
			if x.eit == eit:
				return True
			beg = x.timebegin
			end = x.timeend
			if beginTime > beg and beginTime < end and endTime > end:
				type |= pre
			elif beginTime < beg and endTime > beg and endTime < end:
				type |= post
	if type == 0:
		return True
	elif type == pre:
		return False
	elif type == post:
		return False
	else:
		return True

def isInTimerList(begin, duration, service, eit, timer_list):
	time_match = 0
	chktime = None
	chktimecmp = None
	chktimecmp_end = None
	end = begin + duration
	timerentry = None
	serviceref = getServiceRef(service)
	for x in timer_list:
		if x.servicereference.upper() == serviceref.upper():
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
				if getTimerType(serviceref, begin, duration, eit, timer_list):				
					timerentry = x
				break
	return timerentry

class E2Timer:
	def __init__(self, servicereference = "", servicename = "", name = "", disabled = 0, timebegin = 0, timeend = 0, duration = 0, startprepare = 0, state = 0, repeated = 0, justplay = 0, eit = 0, afterevent = 0, dirname = "", description = "", tags = None):	
		self.servicereference = servicereference
		self.servicename = servicename
		self.name = name
		self.disabled = disabled
		self.timebegin = timebegin
		self.timeend = timeend
		self.duration = duration
		self.startprepare = startprepare
		self.state = state
		self.repeated = repeated
		self.justplay = justplay
		self.afterEvent = afterevent
		self.dirname = dirname
		self.description = description
		###### added to make it work with TimerEdit
		self.begin = timebegin
		self.end = timeend
		self.tags = tags or []
		self.service_ref = ServiceReference(servicereference)
		self.repeatedbegindate = 0
		self.plugins = {}
		self.log_entries = []
		self.eit = eit
	
	def isRunning(self):
		return self.state == 2
		
	def resetRepeated(self):
		self.repeated = int(0)
		
	def setRepeated(self, day):
		self.repeated |= (2 ** day)
		print "Repeated: " + str(self.repeated)
	
def FillE2TimerList(xmlstring, sreference = None):
	E2TimerList = []
	try: root = xml.etree.cElementTree.fromstring(xmlstring)
	except: return E2TimerList
	if sreference is None:
		serviceref = None
	else:
		serviceref = getServiceRef(sreference)

	for timer in root.findall("e2timer"):
		go = False
		state = 0
		try: state = int(timer.findtext("e2state", 0))
		except: state = 0
		disabled = 0
		try: disabled = int(timer.findtext("e2disabled", 0))
		except: disabled = 0
		servicereference = str(timer.findtext("e2servicereference", '').encode("utf-8", 'ignore'))
		if serviceref is None:
			go = True
		else:
			if serviceref.upper() == servicereference.upper() and state != TimerEntry.StateEnded and not disabled:
				go = True
		
		tags = []
		if timer.findtext("e2tags") == "":
			pass
		else:
			tagsList = timer.findtext("e2tags").encode("utf-8", 'ignore').split(" ")
			for tag in tagsList:
				tags.append(tag)
				
		if go:
			timebegin = 0
			timeend = 0
			duration = 0
			startprepare = 0
			repeated = 0
			justplay = 0
			afterevent = 0
			eit = -1
			try: timebegin = int(timer.findtext("e2timebegin", 0))
			except: timebegin = 0
			try: timeend = int(timer.findtext("e2timeend", 0))
			except: timeend = 0
			try: duration = int(timer.findtext("e2duration", 0))
			except: duration = 0
			try: startprepare = int(timer.findtext("e2startprepare", 0))
			except: startprepare = 0
			try: repeated = int(timer.findtext("e2repeated", 0))
			except: repeated = 0
			try: justplay = int(timer.findtext("e2justplay", 0)) 
			except: justplay = 0
			try: afterevent = int(timer.findtext("e2afterevent", 0))
			except: afterevent = 0
			try: eit = int(timer.findtext("e2eit", -1))
			except: eit = -1
			
			E2TimerList.append(E2Timer(
				servicereference = servicereference,
				servicename = str(timer.findtext("e2servicename", 'n/a').encode("utf-8", 'ignore')),
				name = str(timer.findtext("e2name", '').encode("utf-8", 'ignore')),
				disabled = disabled,
				timebegin = timebegin,
				timeend = timeend,
				duration = duration,
				startprepare = startprepare,
				state = state,
				repeated = repeated,
				justplay = justplay,
				eit = eit,
				afterevent = afterevent,
				dirname = str(timer.findtext("e2location", '').encode("utf-8", 'ignore')),
				description = str(timer.findtext("e2description", '').encode("utf-8", 'ignore')),
				tags = tags))
	return E2TimerList
	
def sendPartnerBoxWebCommand(url, timeout=60, username = "root", password = "", webiftype="standard", *args, **kwargs):
	scheme, host, port, path = url_parse(url)
	
	if webiftype == "openwebif":
		d = myconnector.runCommand(path, username, password, host, port, "0")
		
		def returnResult(result):
			return result
			
		d.addCallback(returnResult)
		
		def returnError(error):
			print "[Partnerbox] - Error in sendPartnerBoxWebCommand", error.getErrorMessage()
			return error
		
		d.addErrback(returnError)
		
		return d
	else:			
		d = myconnector.getSessionId(username, password, host, port)
	
		def extractSessionId(result):
			print "[Partnerbox] - got session"
			sessionId = result
	
			e = myconnector.runCommand(path, username,password,host,port, sessionId)
		
			def returnResult(result):
				return result
		
			e.addCallback(returnResult)
			
			def returnError(error):
				print "[Partnerbox] - Error in sendPartnerBoxWebCommand", error.getErrorMessage()
				return error
			
			e.addErrback(returnError)
		
			return e
	
		d.addCallback(extractSessionId)
	
		def returnError(error):
			print "[Partnerbox] - Error in getSessionId", error
		
			return error
		
		d.addErrback(returnError)
	
		return d

def SetPartnerboxTimerlist(partnerboxentry = None, sreference = None):
	global CurrentIP
	if partnerboxentry is None:
		return	
	try:
		password = partnerboxentry.password.value
		username = "root"
		CurrentIP = partnerboxentry.ip.value
		ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
		port = partnerboxentry.port.value
		sCommand = "http://%s:%d/web/timerlist" % (ip,port)
		sendPartnerBoxWebCommand(sCommand, 3, username, password).addCallback(boundFunction(setTimerListCallback, sreference = sreference)).addErrback(setTimerListErrorCallbackError)
		print "[RemoteEPGList] Getting timerlist data from %s..."%ip
		
	except Exception,e: print str(e)

def setTimerListCallback(result, sreference = None):
	global remote_timer_list
	remote_timer_list = FillE2TimerList(result, sreference)
	
def setTimerListErrorCallbackError(error):
	print error.getErrorMessage()

def getServiceRef(sreference):
	serviceref = sreference
	hindex = sreference.find("http")
	if hindex > 0: # partnerbox service ?
		serviceref =  serviceref[:hindex]
	return serviceref
