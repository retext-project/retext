# This file is part of ReText
# Copyright: 2014 Lukas Holecek
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

from FakeVim import FakeVimProxy, FakeVimHandler, FAKEVIM_PYQT_VERSION, \
	MessageError

if FAKEVIM_PYQT_VERSION != 5:
	raise ImportError("FakeVim must be compiled with Qt 5")

from PyQt5.QtCore import QDir, QRegExp, QObject, Qt
from PyQt5.QtGui import QPainter, QPen, QTextCursor
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, \
	QMessageBox, QStatusBar, QTextEdit

class FakeVimMode:
	@staticmethod
	def init(window):
		window.setStatusBar(StatusBar())

	@staticmethod
	def exit(window):
		window.statusBar().deleteLater()

class Proxy (FakeVimProxy):
	""" Used by FakeVim to modify or retrieve editor state. """
	def __init__(self, window, editor, handler):
		super(Proxy, self).__init__(handler.handler())
		self.__handler = handler
		self.__window = window
		self.__editor = editor

		self.__statusMessage = ""
		self.__statusData = ""
		self.__cursorPosition =  -1
		self.__cursorAnchor =  -1
		self.__eventFilter = None

		self.__lastSavePath = ""

	def showMessage(self, messageLevel, message):
		self.__handler.handler().showMessage(messageLevel, message)

	def needSave(self):
		return self.__editor.document().isModified()

	def maybeCloseEditor(self):
		if self.needSave():
			self.showMessage( MessageError,
					self.tr("No write since last change (add ! to override)") )
			self.__updateStatusBar()

			return False

		return True

	def commandQuit(self):
		self.__handler.quit()

	def commandWrite(self):
		self.__handler.save()
		return not self.needSave()

	def handleExCommand(self, cmd):
		if cmd.matches("q", "quit"):
			if cmd.hasBang or self.maybeCloseEditor():
				self.commandQuit()
		elif cmd.matches("w", "write"):
			self.commandWrite()
		elif cmd.cmd == "wq":
			self.commandWrite() and self.commandQuit()
		else:
			return False
		return True

	def enableBlockSelection(self, cursor):
		self.__handler.setBlockSelection(True)
		self.__editor.setTextCursor(cursor)

	def disableBlockSelection(self):
		self.__handler.setBlockSelection(False)

	def blockSelection(self):
		self.__handler.setBlockSelection(True)
		return self.__editor.textCursor()

	def hasBlockSelection(self):
		return self.__handler.hasBlockSelection()

	def commandBufferChanged(self, msg, cursorPosition, cursorAnchor, messageLevel, eventFilter):
		# Give focus back to editor if closing command line.
		if self.__cursorPosition != -1 and cursorPosition == -1:
			self.__editor.setFocus()

		self.__cursorPosition = cursorPosition
		self.__cursorAnchor = cursorAnchor
		self.__statusMessage = msg
		self.__updateStatusBar();
		self.__eventFilter = eventFilter

	def statusDataChanged(self, msg):
		self.__statusData = msg
		self.__updateStatusBar()

	def extraInformationChanged(self, msg):
		QMessageBox.information(self.__window, self.tr("Information"), msg)

	def highlightMatches(self, pattern):
		self.__handler.highlightMatches(pattern)

	def __updateStatusBar(self):
		self.__window.statusBar().setStatus(
				self.__statusMessage, self.__statusData,
				self.__cursorPosition, self.__cursorAnchor, self.__eventFilter)

class BlockSelection (QWidget):
	def __init__(self, editor):
		super(BlockSelection, self).__init__(editor.viewport())
		self.__editor = editor
		self.__lineWidth = 4

	def updateSelection(self, tc):
		# block selection rectagle
		rect = self.__editor.cursorRect(tc)
		w = rect.width()
		tc2 = QTextCursor(tc)
		tc2.setPosition(tc.anchor())
		rect = rect.united( self.__editor.cursorRect(tc2) )
		x = self.__lineWidth / 2
		rect.adjust(-x, -x, x - w, x)

		QWidget.setGeometry(self, rect)

	def paintEvent(self, paintEvent):
		painter = QPainter(self)
		painter.setClipRect(paintEvent.rect())

		color = self.__editor.palette().text()
		painter.setPen(QPen(color, self.__lineWidth))
		painter.drawRect(self.rect())

class ReTextFakeVimHandler (QObject):
	""" Editor widget driven by FakeVim. """
	def __init__(self, editor, window):
		super(ReTextFakeVimHandler, self).__init__(window)

		self.__window = window
		self.__editor = editor

		self.__blockSelection = BlockSelection(self.__editor)
		self.__blockSelection.hide()

		self.__searchSelections = []

		fm = self.__editor.fontMetrics()
		self.__cursorWidth = fm.averageCharWidth()
		self.__oldCursorWidth = self.__editor.cursorWidth()
		self.__editor.setCursorWidth(self.__cursorWidth)

		self.__handler = FakeVimHandler(self.__editor, self)
		self.__proxy = Proxy(self.__window, self.__editor, self)

		self.__handler.installEventFilter()
		self.__handler.setupWidget()
		self.__handler.handleCommand(
				'source {home}/.vimrc'.format(home = QDir.homePath()))

		self.__saveAction = None
		self.__quitAction = None

		# Update selections if cursor changes because of current line can be highlighted.
		self.__editor.cursorPositionChanged.connect(self.__updateSelections)

	def remove(self):
		self.__editor.setOverwriteMode(False)
		self.__editor.setCursorWidth(self.__oldCursorWidth)
		self.__blockSelection.deleteLater()
		self.__updateSelections([])
		self.deleteLater()

	def handler(self):
		return self.__handler

	def setBlockSelection(self, enabled):
		self.__editor.setCursorWidth(self.__cursorWidth)
		self.__blockSelection.setVisible(enabled)

		if enabled:
			self.__blockSelection.updateSelection(self.__editor.textCursor())

			# Shift text cursor into the block selection.
			tc = self.__editor.textCursor()
			if self.__columnForPosition(tc.anchor()) < self.__columnForPosition(tc.position()):
				self.__editor.setCursorWidth(-self.__cursorWidth)

	def setSaveAction(self, saveAction):
		self.__saveAction = saveAction

	def setQuitAction(self, quitAction):
		self.__quitAction = quitAction

	def save(self):
		if self.__saveAction:
			self.__saveAction.trigger()

	def quit(self):
		if self.__quitAction:
			self.__quitAction.trigger()

	def hasBlockSelection(self):
		return self.__blockSelection.isVisible()

	def highlightMatches(self, pattern):
		cur = self.__editor.textCursor()

		re = QRegExp(pattern)
		cur = self.__editor.document().find(re)
		a = cur.position()

		searchSelections = []

		while not cur.isNull():
			if cur.hasSelection():
				selection = QTextEdit.ExtraSelection()
				selection.format.setBackground(Qt.yellow)
				selection.format.setForeground(Qt.black)
				selection.cursor = cur
				searchSelections.append(selection)
			else:
				cur.movePosition(QTextCursor.NextCharacter)

			cur = self.__editor.document().find(re, cur)
			b = cur.position()

			if a == b:
				cur.movePosition(QTextCursor.NextCharacter)
				cur = self.__editor.document().find(re, cur)
				b = cur.position()

				if (a == b):
					break
			a = b

		self.__updateSelections(searchSelections)

	def __updateSelections(self, searchSelections = None):
		oldSelections = self.__editor.extraSelections()

		for selection in self.__searchSelections:
			for i in range(len(oldSelections) - 1, 0, -1):
				if selection.cursor == oldSelections[i].cursor:
					oldSelections.pop(i)
					break

		if searchSelections != None:
			self.__searchSelections = searchSelections

		self.__editor.setExtraSelections(oldSelections + self.__searchSelections)

	def __columnForPosition(self, position):
		return position - self.__editor.document().findBlock(position).position()

class StatusBar (QStatusBar):
	def __init__(self):
		super(StatusBar, self).__init__()

		self.__statusMessageLabel = QLabel(self)
		self.__statusDataLabel = QLabel(self)
		self.__commandLine = QLineEdit(self)

		self.addPermanentWidget(self.__statusMessageLabel, 1)
		self.addPermanentWidget(self.__commandLine, 1)
		self.addPermanentWidget(self.__statusDataLabel)

		self.__commandLine.hide()

	def setStatus(self, statusMessage, statusData, cursorPosition, cursorAnchor, eventFilter):
		commandMode = cursorPosition != -1
		self.__commandLine.setVisible(commandMode)
		self.__statusMessageLabel.setVisible(not commandMode)

		if commandMode:
			self.__commandLine.installEventFilter(eventFilter)
			self.__commandLine.setFocus()
			self.__commandLine.setText(statusMessage)
			self.__commandLine.setSelection(cursorPosition, cursorAnchor - cursorPosition)
		else:
			self.__statusMessageLabel.setText(statusMessage)

		self.__statusDataLabel.setText(statusData)
