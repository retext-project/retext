# vim: ts=8:sts=8:sw=8:noexpandtab
#
# This file is part of ReText
# Copyright: 2017 Dmitry Shachnev
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

from PyQt5.QtCore import QDir
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QTextBrowser
from ReText import globalSettings

class ReTextPreview(QTextBrowser):

	def __init__(self, tab):
		QTextBrowser.__init__(self)
		self.tab = tab
		# if set to True, links to other files will unsuccessfully be opened as anchors
		self.setOpenLinks(False)
		self.anchorClicked.connect(self.openInternal)

	def disconnectExternalSignals(self):
		pass

	def openInternal(self, link):
		url = link.url()
		isLocalHtml = (link.scheme() in ('file', '') and url.endswith('.html'))
		if url.startswith('#'):
			self.scrollToAnchor(url[1:])
		elif link.isRelative():
			fileToOpen = QDir.current().filePath(url)
			if self.tab.openSourceFile(fileToOpen):
				return
		if globalSettings.handleWebLinks and isLocalHtml:
			self.setSource(link)
		else:
			QDesktopServices.openUrl(link)


class ReTextWebPreview:
	"""This is a common class shared between WebKit and WebEngine
	based previews."""

	def __init__(self, editBox):
		self.editBox = editBox

		self.settings().setDefaultTextEncoding('utf-8')

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

	def _handleCursorPositionChanged(self):
		editorCursorPosition = self.editBox.verticalScrollBar().value() + \
				       self.editBox.cursorRect().top()
		self.syncscroll.handleCursorPositionChanged(editorCursorPosition)

	def _handleEditorResized(self, rect):
		self.syncscroll.handleEditorResized(rect.height())
