# vim: ts=8:sts=8:sw=8:noexpandtab
#
# This file is part of ReText
# Copyright: 2015-2016 Dmitry Shachnev
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

from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWebKit import QWebSettings
from PyQt5.QtWebKitWidgets import QWebPage, QWebView


class ReTextWebPreview(QWebView):

	def __init__(self, editBox,
	             editorPositionToSourceLineFunc,
	             sourceLineToEditorPositionFunc):

		QWebView.__init__(self)

		self.editBox = editBox

		if not globalSettings.handleWebLinks:
			self.page().setLinkDelegationPolicy(QWebPage.DelegateExternalLinks)
			self.page().linkClicked.connect(QDesktopServices.openUrl)
		self.settings().setAttribute(QWebSettings.LocalContentCanAccessFileUrls, False)
		self.settings().setDefaultTextEncoding('utf-8')
		# Avoid caching of CSS
		self.settings().setObjectCacheCapacities(0,0,0)

		self.syncscroll = SyncScroll(self.page().mainFrame(),
					     editorPositionToSourceLineFunc,
					     sourceLineToEditorPositionFunc)

		# Events relevant to sync scrolling
		self.editBox.cursorPositionChanged.connect(self._handleCursorPositionChanged)
		self.editBox.verticalScrollBar().valueChanged.connect(self.syncscroll.handleEditorScrolled)
		self.editBox.resized.connect(self._handleEditorResized)

		# Scroll the preview when the mouse wheel is used to scroll
		# beyond the beginning/end of the editor
		self.editBox.scrollLimitReached.connect(self._handleWheelEvent)

	def disconnectExternalSignals(self):
		self.editBox.cursorPositionChanged.disconnect(self._handleCursorPositionChanged)
		self.editBox.verticalScrollBar().valueChanged.disconnect(self.syncscroll.handleEditorScrolled)
		self.editBox.resized.disconnect(self._handleEditorResized)

		self.editBox.scrollLimitReached.disconnect(self._handleWheelEvent)

	def _handleWheelEvent(self, event):
		"""
		Use this intermediate function because it is not possible to
		disconnect a built-in method. It would generate the following error:
		  TypeError: 'builtin_function_or_method' object is not connected
		"""
		# Only pass wheelEvents on to the preview if syncscroll is
		# controlling the position of the preview
		if self.syncscroll.isActive():
			self.wheelEvent(event)

	def _handleCursorPositionChanged(self):
		editorCursorPosition = self.editBox.verticalScrollBar().value() + \
				       self.editBox.cursorRect().top()
		self.syncscroll.handleCursorPositionChanged(editorCursorPosition)

	def _handleEditorResized(self, rect):
		self.syncscroll.handleEditorResized(rect.height())

	def updateFontSettings(self):
		settings = self.settings()
		settings.setFontFamily(QWebSettings.StandardFont,
		                       globalSettings.font.family())
		settings.setFontSize(QWebSettings.DefaultFontSize,
		                     globalSettings.font.pointSize())
