# vim: ts=8:sts=8:sw=8:noexpandtab
#
# This file is part of ReText
# Copyright: 2017-2021 Dmitry Shachnev
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

from os.path import exists
import time
from PyQt5.QtCore import QDir, QUrl, Qt
from PyQt5.QtGui import QDesktopServices, QGuiApplication, QTextCursor, QTextDocument
from PyQt5.QtWidgets import QTextBrowser
from ReText import globalSettings

class ReTextPreview(QTextBrowser):

	def __init__(self, tab):
		QTextBrowser.__init__(self)
		self.tab = tab
		# if set to True, links to other files will unsuccessfully be opened as anchors
		self.setOpenLinks(False)
		self.anchorClicked.connect(self.openInternal)
		self.lastRenderTime = 0
		self.distToBottom = None
		self.verticalScrollBar().rangeChanged.connect(self.updateScrollPosition)

	def disconnectExternalSignals(self):
		pass

	def openInternal(self, link):
		url = link.url()
		if url.startswith('#'):
			self.scrollToAnchor(url[1:])
			return
		elif link.isRelative():
			fileToOpen = QDir.current().filePath(url)
		else:
			fileToOpen = link.toLocalFile() if link.isLocalFile() else None
		if fileToOpen is not None:
			if exists(fileToOpen):
				link = QUrl.fromLocalFile(fileToOpen)
				if globalSettings.handleWebLinks and fileToOpen.endswith('.html'):
					self.setSource(link)
					return
			# This is outside the "if exists" block because we can prompt for
			# creating the file
			if self.tab.openSourceFile(fileToOpen):
				return
		QDesktopServices.openUrl(link)

	def findText(self, text, flags, wrap=False):
		cursor = self.textCursor()
		if wrap and flags & QTextDocument.FindFlag.FindBackward:
			cursor.movePosition(QTextCursor.MoveOperation.End)
		elif wrap:
			cursor.movePosition(QTextCursor.MoveOperation.Start)
		newCursor = self.document().find(text, cursor, flags)
		if not newCursor.isNull():
			self.setTextCursor(newCursor)
			return True
		if not wrap:
			return self.findText(text, flags, wrap=True)
		return False

	def updateScrollPosition(self, minimum, maximum):
		"""Called when vertical scroll bar range changes.

		If this happened during preview rendering (less than 0.5s since it
		was started), set the position such that distance to bottom is the
		same as before refresh.
		"""
		timeSinceRender = time.time() - self.lastRenderTime
		if timeSinceRender < 0.5 and self.distToBottom is not None and maximum:
			newValue = maximum - self.distToBottom
			if newValue >= minimum:
				self.verticalScrollBar().setValue(newValue)

	def setFont(self, font):
		self.document().setDefaultFont(font)


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

	def wheelEvent(self, event):
		if QGuiApplication.keyboardModifiers() == Qt.KeyboardModifier.ControlModifier:
			zoomFactor = self.zoomFactor()
			zoomFactor *= 1.001 ** event.angleDelta().y()
			self.setZoomFactor(zoomFactor)
		return super().wheelEvent(event)
