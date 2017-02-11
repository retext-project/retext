# vim: ts=8:sts=8:sw=8:noexpandtab
#
# This file is part of ReText
# Copyright: 2015-2017 Dmitry Shachnev
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


from ReText import globalSettings
from ReText.syncscroll import SyncScroll
from ReText.preview import ReTextWebPreview

from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtWebKitWidgets import QWebPage, QWebView


class ReTextWebKitPreview(ReTextWebPreview, QWebView):

	def __init__(self, tab,
	             editorPositionToSourceLineFunc,
	             sourceLineToEditorPositionFunc):

		QWebView.__init__(self)
		self.tab = tab

		self.syncscroll = SyncScroll(self.page().mainFrame(),
		                             editorPositionToSourceLineFunc,
		                             sourceLineToEditorPositionFunc)
		ReTextWebPreview.__init__(self, tab.editBox)

		self.page().setLinkDelegationPolicy(QWebPage.DelegateAllLinks)
		self.page().linkClicked.connect(self._handleLinkClicked)
		self.settings().setAttribute(QWebSettings.LocalContentCanAccessFileUrls, False)
		# Avoid caching of CSS
		self.settings().setObjectCacheCapacities(0,0,0)

	def updateFontSettings(self):
		settings = self.settings()
		settings.setFontFamily(QWebSettings.StandardFont,
		                       globalSettings.font.family())
		settings.setFontSize(QWebSettings.DefaultFontSize,
		                     globalSettings.font.pointSize())

	def _handleWheelEvent(self, event):
		# Only pass wheelEvents on to the preview if syncscroll is
		# controlling the position of the preview
		if self.syncscroll.isActive():
			self.wheelEvent(event)

	def _handleLinkClicked(self, url):
		if url.isLocalFile():
			localFile = url.toLocalFile()
			if localFile == self.tab.fileName and url.hasFragment():
				self.page().mainFrame().scrollToAnchor(url.fragment())
				return
			if self.tab.openSourceFile(localFile):
				return
		if globalSettings.handleWebLinks:
			self.load(url)
		else:
			QDesktopServices.openUrl(url)
