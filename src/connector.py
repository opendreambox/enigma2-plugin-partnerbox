#
#  connector
#
#  Coded by dre (c) 2017
#  Support: board.dreambox.tools
#  e-Mail: dre@dreambox.tools
#
#  This software is open source but it is NOT free software.
#  
#  This software may only be distributed to and executed on hardware which
#  is licensed by Dream Property GmbH.
#  In other words:
#  It's NOT allowed to distribute any parts of this software or its source code in ANY way
#  to hardware which is NOT licensed by Dream Property GmbH.
#  It's NOT allowed to execute this software and its source code or even parts of it in
#  ANY way on hardware which is NOT licensed by Dream Property GmbH.
#
#  If you want to use or modify the code or parts of it,
#  you have to keep MY license and inform me about the modifications by mail.
#
#  connector is a piece of software that handles calls to the webinterface of a
#  Dreambox with activated enhanced security features (but works as well having them
#  switched off).
#  It offers two functions:
#  - getSession: this function must be called first to get a sessionid which is a pre-
#    condition for the second function to work
#  - runCommand: this function executes the call and ensures all data is correctly
#    handed over via a POST request
#
#  When using this software the chain of commands (getSession -> runCommand) is simplest
#  implemented as inline callbacks with the call of runCommand being placed in the 
#  callback of getSession:
#	d = connector.getSessionId(params)
#
#	def handleResult(session):
#		e = connector.runCommand(params)
#
# 		def returnResult(result):
#  			return result
#		e.addCallback(returnResult)
#
#		def returnError(error):
#			print error.getErrorMessage()
#	  	e.addErrback(returnError)
#		return e
#
#	d.addCallback(handleResult)
#
#	def returnError(error):
#		print error.getErrorMessage()
#
#	d.addErrback(returnError)
#	return d
		


import urllib, urllib2
import xml.etree.cElementTree
from twisted.web.client import getPage
from twisted.internet import reactor, defer
from base64 import encodestring

# run a command and return the result
def runCommand(target, username="", password="", host="", port=80, sessionid = "0", **kwargs):
	command = "http://%s:%d%s" %(host, port, target)

	print "[Connector] - Running command ", command

	basicAuth = encodestring(("%s:%s")%(username,password))
	authHeader = "Basic " + basicAuth.strip()
	
	headers = {
		"Authorization": authHeader,
		'content-type':'application/x-www-form-urlencoded',	
	}
	
	postdata = {"user":username, "password":password, "sessionid":sessionid}

	for key, value in kwargs.iteritems():
		postdata.update({key : value })
	
		
	d = getPage('%s' %(command), method='POST', headers = headers, postdata=urllib.urlencode(postdata))
	
	def readData(data):
		return data
		
	d.addCallback(readData)
	
	def printError(error):
		print "[Connector] - Error in runCommand", error
		return error
		
	d.addErrback(printError)
	
	return d
	
# get a session id
def getSessionId(username = "", password = "", host = "", port = 80):
	command = "http://%s:%d/web/session" % (host, port)

	print "[Connector] - Running command ", command
	
	basicAuth = encodestring(("%s:%s")%(username,password))
	authHeader = "Basic " + basicAuth.strip()
	headers = {
					"Authorization": authHeader,					
					"content-type" : "application/x-www-form-urlencoded",
				  }

	postdata = urllib.urlencode(dict(user=username, password=password))
	d = getPage('%s' %(command), method='GET', headers = headers, postdata=postdata)	
	
	def readSessionId(result):
		print "[Connector] - Read sessionId"
		try: 
			root = xml.etree.cElementTree.fromstring(result)
		except:
			return "0"
		return root.text
		
	d.addCallback(readSessionId)
		
	def printError(error):
		print "[Connector] - Error in getSessionId", error
		return error
		
	d.addErrback(printError)
	
	return d
