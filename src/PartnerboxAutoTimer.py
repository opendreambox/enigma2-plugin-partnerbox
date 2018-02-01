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

from Screens.MessageBox import MessageBox
from Components.config import config
from PartnerboxFunctions import sendPartnerBoxWebCommand
from PartnerboxSetup import PartnerboxEntriesListConfigScreen
from Plugins.Extensions.AutoTimer.AutoTimerEditor import AutoTimerEditor, AutoTimerEPGSelection, addAutotimerFromEvent


class PartnerboxAutoTimer(object):
	instance = None
	def __init__(self, session):
		self.session = session
		assert not PartnerboxAutoTimer.instance, "only one PartnerboxAutoTimer instance is allowed!"
		PartnerboxAutoTimer.instance = self # set instance

	def setPartnerboxAutoTimer(self, ret):
		if ret:
			from Plugins.Extensions.AutoTimer.plugin import	autotimer
			parameter = {'xml': autotimer.writeXmlTimer(ret) }
			count = config.plugins.Partnerbox.entriescount.value
			if count == 1:
				self.partnerboxplugin(None, parameter, config.plugins.Partnerbox.Entries[0])
			else:
				self.session.openWithCallback(self.partnerboxplugin, PartnerboxEntriesListConfigScreen, parameter)

	def partnerboxplugin(self, unUsed, parameter, partnerboxentry = None):
		if partnerboxentry is None:
			return

		ip = "%d.%d.%d.%d" % tuple(partnerboxentry.ip.value)
		port = partnerboxentry.port.value
		username = "root"
		password = partnerboxentry.password.value
		webiftype = partnerboxentry.webinterfacetype.value		
		sCommand = "http://%s:%d/autotimer/add_xmltimer" % (ip,port)
		sendPartnerBoxWebCommand(sCommand, 10, username, password, webiftype, None, parameter=parameter).addCallback(self.downloadCallback).addErrback(self.downloadError)


	def downloadCallback(self, result = None):
		self.session.open(MessageBox,_("AutoTimer was added successfully"),  MessageBox.TYPE_INFO)

	def downloadError(self, error = None):
		if error is not None:
			self.session.open(MessageBox,str(error.getErrorMessage()),  MessageBox.TYPE_INFO)

	def autotimerImporterCallback(self, ret):
		if ret:
			ret, session = ret
			session.openWithCallback(self.setPartnerboxAutoTimer, AutoTimerEditor,ret)

class PartnerboxAutoTimerEPGSelection(AutoTimerEPGSelection):
	def __init__(self, *args):
		AutoTimerEPGSelection.__init__(self, *args)

	def timerAdd(self):
		cur = self["list"].getCurrent()
		evt = cur[0]
		sref = cur[1]
		if not evt:
			return

		addAutotimerFromEvent(self.session, evt = evt, service = sref, importer_Callback = PartnerboxAutoTimer.instance.autotimerImporterCallback)



