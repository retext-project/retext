# vim: ts=8:sts=8:sw=8:noexpandtab
#
# This file is part of ReText
# Copyright: 2012-2017 Dmitry Shachnev
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

import os
import re
import weakref

from markups import MarkdownMarkup, ReStructuredTextMarkup, TextileMarkup
from ReText import globalSettings, tablemode, readFromSettings

from PyQt5.QtCore import pyqtSignal, QFileInfo, QPoint, QRect, QSize, Qt
from PyQt5.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter, \
QPalette, QTextCursor, QTextFormat, QWheelEvent
from PyQt5.QtWidgets import QFileDialog, QLabel, QTextEdit, QWidget

try:
	from ReText.fakevimeditor import ReTextFakeVimHandler
except ImportError:
	ReTextFakeVimHandler = None

colors = {
	'marginLine': QColor(0xdc, 0xd2, 0xdc),
	'currentLineHighlight': QColor(0xff, 0xff, 0xc8),
	'infoArea': QColor(0xaa, 0xff, 0x55, 0xaa),
	'lineNumberArea': Qt.cyan,
	'lineNumberAreaText': Qt.darkCyan
}

colorValues = {
	colorName: readFromSettings(
		'ColorScheme/' + colorName, QColor, default=colors[colorName])
	for colorName in colors
}

def documentIndentMore(document, cursor, globalSettings=globalSettings):
	if cursor.hasSelection():
		block = document.findBlock(cursor.selectionStart())
		end = document.findBlock(cursor.selectionEnd()).next()
		cursor.beginEditBlock()
		while block != end:
			cursor.setPosition(block.position())
			if globalSettings.tabInsertsSpaces:
				cursor.insertText(' ' * globalSettings.tabWidth)
			else:
				cursor.insertText('\t')
			block = block.next()
		cursor.endEditBlock()
	else:
		indent = globalSettings.tabWidth - (cursor.positionInBlock()
			% globalSettings.tabWidth)
		if globalSettings.tabInsertsSpaces:
			cursor.insertText(' ' * indent)
		else:
			cursor.insertText('\t')

def documentIndentLess(document, cursor, globalSettings=globalSettings):
	if cursor.hasSelection():
		block = document.findBlock(cursor.selectionStart())
		end = document.findBlock(cursor.selectionEnd()).next()
	else:
		block = document.findBlock(cursor.position())
		end = block.next()
	cursor.beginEditBlock()
	while block != end:
		cursor.setPosition(block.position())
		if document.characterAt(cursor.position()) == '\t':
			cursor.deleteChar()
		else:
			pos = 0
			while document.characterAt(cursor.position()) == ' ' \
			and pos < globalSettings.tabWidth:
				pos += 1
				cursor.deleteChar()
		block = block.next()
	cursor.endEditBlock()

class ReTextEdit(QTextEdit):
	resized = pyqtSignal(QRect)
	scrollLimitReached = pyqtSignal(QWheelEvent)

	def __init__(self, parent):
		QTextEdit.__init__(self)
		self.tab = weakref.proxy(parent)
		self.parent = parent.p
		self.undoRedoActive = False
		self.tableModeEnabled = False
		self.setAcceptRichText(False)
		self.lineNumberArea = LineNumberArea(self)
		self.infoArea = InfoArea(self)
		self.updateFont()
		self.document().blockCountChanged.connect(self.updateLineNumberAreaWidth)
		self.cursorPositionChanged.connect(self.highlightCurrentLine)
		self.document().contentsChange.connect(self.contentsChange)
		if globalSettings.useFakeVim:
			self.installFakeVimHandler()

	def updateFont(self):
		self.setFont(globalSettings.editorFont)
		metrics = self.fontMetrics()
		self.marginx = (self.document().documentMargin()
			+ metrics.width(' ' * globalSettings.rightMargin))
		self.setTabStopWidth(globalSettings.tabWidth * self.fontMetrics().width(' '))
		self.updateLineNumberAreaWidth()
		self.infoArea.updateTextAndGeometry()

	def paintEvent(self, event):
		if not globalSettings.rightMargin:
			return QTextEdit.paintEvent(self, event)
		painter = QPainter(self.viewport())
		painter.setPen(colorValues['marginLine'])
		y1 = self.rect().topLeft().y()
		y2 = self.rect().bottomLeft().y()
		painter.drawLine(self.marginx, y1, self.marginx, y2)
		QTextEdit.paintEvent(self, event)

	def wheelEvent(self, event):
		QTextEdit.wheelEvent(self, event)

		if event.angleDelta().y() < 0:
			scrollBarLimit = self.verticalScrollBar().maximum()
		else:
			scrollBarLimit = self.verticalScrollBar().minimum()

		if self.verticalScrollBar().value() == scrollBarLimit:
			self.scrollLimitReached.emit(event)

	def scrollContentsBy(self, dx, dy):
		QTextEdit.scrollContentsBy(self, dx, dy)
		self.lineNumberArea.update()

	def contextMenuEvent(self, event):
		text = self.toPlainText()
		dictionary = self.tab.highlighter.dictionary
		if (dictionary is None) or not text:
			return QTextEdit.contextMenuEvent(self, event)
		oldcursor = self.textCursor()
		cursor = self.cursorForPosition(event.pos())
		curchar = self.document().characterAt(cursor.position())
		isalpha = curchar.isalpha()
		cursor.select(QTextCursor.WordUnderCursor)
		if not isalpha or (oldcursor.hasSelection() and
		oldcursor.selectedText() != cursor.selectedText()):
			return QTextEdit.contextMenuEvent(self, event)
		self.setTextCursor(cursor)
		word = cursor.selectedText()
		if not word or dictionary.check(word):
			self.setTextCursor(oldcursor)
			return QTextEdit.contextMenuEvent(self, event)
		suggestions = dictionary.suggest(word)
		actions = [self.parent.act(sug, trig=self.fixWord(sug)) for sug in suggestions]
		menu = self.createStandardContextMenu()
		menu.insertSeparator(menu.actions()[0])
		for action in actions[::-1]:
			menu.insertAction(menu.actions()[0], action)
		menu.exec(event.globalPos())

	def fixWord(self, correctword):
		return lambda: self.insertPlainText(correctword)

	def keyPressEvent(self, event):
		key = event.key()
		cursor = self.textCursor()
		if key == Qt.Key_Backspace and event.modifiers() & Qt.GroupSwitchModifier:
			# Workaround for https://bugreports.qt.io/browse/QTBUG-49771
			event = QKeyEvent(event.type(), event.key(),
				event.modifiers() ^ Qt.GroupSwitchModifier)
		if key == Qt.Key_Tab:
			documentIndentMore(self.document(), cursor)
		elif key == Qt.Key_Backtab:
			documentIndentLess(self.document(), cursor)
		elif key == Qt.Key_Return:
			markupClass = self.tab.getActiveMarkupClass()
			if event.modifiers() & Qt.ControlModifier:
				cursor.insertText('\n')
				self.ensureCursorVisible()
			elif self.tableModeEnabled and tablemode.handleReturn(cursor, markupClass,
					newRow=(event.modifiers() & Qt.ShiftModifier)):
				self.setTextCursor(cursor)
				self.ensureCursorVisible()
			else:
				if event.modifiers() & Qt.ShiftModifier and markupClass == MarkdownMarkup:
					# Insert Markdown-style line break
					cursor.insertText('  ')
				self.handleReturn(cursor)
		else:
			if event.text() and self.tableModeEnabled:
				cursor.beginEditBlock()
			QTextEdit.keyPressEvent(self, event)
			if event.text() and self.tableModeEnabled:
				cursor.endEditBlock()

	def handleReturn(self, cursor):
		# Select text between the cursor and the line start
		cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
		text = cursor.selectedText()
		length = len(text)
		pos = 0
		while pos < length and (text[pos] in (' ', '\t')
		  or text[pos:pos+2] in ('* ', '- ')):
			pos += 1
		if pos == length:
			cursor.removeSelectedText()
		# Reset the cursor
		cursor = self.textCursor()
		cursor.insertText(('\n' + text[:pos]) if pos < length else '\n')
		self.ensureCursorVisible()

	def lineNumberAreaWidth(self):
		if not globalSettings.lineNumbersEnabled:
			return 0
		cursor = QTextCursor(self.document())
		cursor.movePosition(QTextCursor.End)
		digits = len(str(cursor.blockNumber() + 1))
		return 5 + self.fontMetrics().width('9') * digits

	def updateLineNumberAreaWidth(self, blockcount=0):
		self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

	def resizeEvent(self, event):
		QTextEdit.resizeEvent(self, event)
		rect = self.contentsRect()
		self.resized.emit(rect)
		self.lineNumberArea.setGeometry(rect.left(), rect.top(),
			self.lineNumberAreaWidth(), rect.height())
		self.infoArea.updateTextAndGeometry()

	def highlightCurrentLine(self):
		if not globalSettings.highlightCurrentLine:
			return self.setExtraSelections([])
		selection = QTextEdit.ExtraSelection();
		selection.format.setBackground(colorValues['currentLineHighlight'])
		selection.format.setProperty(QTextFormat.FullWidthSelection, True)
		selection.cursor = self.textCursor()
		selection.cursor.clearSelection()
		self.setExtraSelections([selection])

	def enableTableMode(self, enable):
		self.tableModeEnabled = enable

	def backupCursorPositionOnLine(self):
		return self.textCursor().positionInBlock()

	def restoreCursorPositionOnLine(self, positionOnLine):
		cursor = self.textCursor()
		cursor.setPosition(cursor.block().position() + positionOnLine)
		self.setTextCursor(cursor)

	def contentsChange(self, pos, removed, added):
		if self.tableModeEnabled:
			markupClass = self.tab.getActiveMarkupClass()

			cursorPosition = self.backupCursorPositionOnLine()
			tablemode.adjustTableToChanges(self.document(), pos, added - removed, markupClass)
			self.restoreCursorPositionOnLine(cursorPosition)
		self.lineNumberArea.update()

	def canInsertFromMimeData(self, mimeData):
		return mimeData.hasText() or mimeData.hasImage()

	def findNextImageName(self, filenames):
		highestNumber = 0
		for filename in filenames:
			m = re.match(r'image(\d+).png', filename, re.IGNORECASE)
			if m:
				number = int(m.group(1))
				highestNumber = max(number, highestNumber)
		return 'image%04d.png' % (highestNumber + 1)

	def getImageFilenameAndLink(self):
		if self.tab.fileName:
			saveDir = os.path.dirname(self.tab.fileName)
		else:
			saveDir = os.getcwd()

		imageFileName = self.findNextImageName(os.listdir(saveDir))

		chosenFileName = QFileDialog.getSaveFileName(self,
		                                   self.tr('Save image'),
		                                   os.path.join(saveDir, imageFileName),
		                                   self.tr('Images (*.png *.jpg)'))[0]

		if chosenFileName:
			# Use relative links for named documents
			if self.tab.fileName:
				try:
					link = os.path.relpath(chosenFileName, saveDir)
				except ValueError:  # different roots
					link = chosenFileName
			else:
				link = chosenFileName
		else:
			link = None

		return chosenFileName, link

	def insertFromMimeData(self, mimeData):
		if mimeData.hasImage():
			fileName, link = self.getImageFilenameAndLink()
			if fileName:
				image = QImage(mimeData.imageData())
				image.save(fileName)

				markupClass = self.tab.getActiveMarkupClass()
				if markupClass == MarkdownMarkup:
					imageText = '![%s](%s)' % (QFileInfo(link).baseName(), link)
				elif markupClass == ReStructuredTextMarkup:
					imageText = '.. image:: %s' % link
				elif markupClass == TextileMarkup:
					imageText = '!%s!' % link

				self.textCursor().insertText(imageText)
		else:
			QTextEdit.insertFromMimeData(self, mimeData)

	def installFakeVimHandler(self):
		if ReTextFakeVimHandler:
			fakeVimEditor = ReTextFakeVimHandler(self, self.parent)
			fakeVimEditor.setSaveAction(self.parent.actionSave)
			fakeVimEditor.setQuitAction(self.parent.actionQuit)
			self.parent.actionFakeVimMode.triggered.connect(fakeVimEditor.remove)

class LineNumberArea(QWidget):
	def __init__(self, editor):
		QWidget.__init__(self, editor)
		self.editor = editor

	def sizeHint(self):
		return QSize(self.editor.lineNumberAreaWidth(), 0)

	def paintEvent(self, event):
		if not globalSettings.lineNumbersEnabled:
			return QWidget.paintEvent(self, event)
		painter = QPainter(self)
		painter.fillRect(event.rect(), colorValues['lineNumberArea'])
		painter.setPen(colorValues['lineNumberAreaText'])
		cursor = self.editor.cursorForPosition(QPoint(0, 0))
		atEnd = False
		fontHeight = self.fontMetrics().height()
		height = self.editor.height()
		while not atEnd:
			rect = self.editor.cursorRect(cursor)
			if rect.top() >= height:
				break
			number = str(cursor.blockNumber() + 1)
			painter.drawText(0, rect.top(), self.width() - 2,
			                 fontHeight, Qt.AlignRight, number)
			cursor.movePosition(QTextCursor.EndOfBlock)
			atEnd = cursor.atEnd()
			if not atEnd:
				cursor.movePosition(QTextCursor.NextBlock)

class InfoArea(QLabel):
	def __init__(self, editor):
		QWidget.__init__(self, editor)
		self.editor = editor
		self.editor.cursorPositionChanged.connect(self.updateTextAndGeometry)
		self.updateTextAndGeometry()
		self.setAutoFillBackground(True)
		palette = self.palette()
		palette.setColor(QPalette.Window, colorValues['infoArea'])
		self.setPalette(palette)
		self.setCursor(Qt.IBeamCursor)

	def updateTextAndGeometry(self):
		text = self.getText()
		self.setText(text)
		viewport = self.editor.viewport()
		metrics = self.fontMetrics()
		width = metrics.width(text)
		height = metrics.height()
		self.resize(width, height)
		rightSide = viewport.width() + self.editor.lineNumberAreaWidth()
		self.move(rightSide - width, viewport.height() - height)
		self.setVisible(not globalSettings.useFakeVim)

	def getText(self):
		template = '%d : %d'
		cursor = self.editor.textCursor()
		block = cursor.blockNumber() + 1
		position = cursor.positionInBlock()
		return template % (block, position)

	def enterEvent(self, event):
		palette = self.palette()
		windowColor = QColor(colorValues['infoArea'])
		windowColor.setAlpha(0x20)
		palette.setColor(QPalette.Window, windowColor)
		textColor = palette.color(QPalette.WindowText)
		textColor.setAlpha(0x20)
		palette.setColor(QPalette.WindowText, textColor)
		self.setPalette(palette)

	def leaveEvent(self, event):
		palette = self.palette()
		palette.setColor(QPalette.Window, colorValues['infoArea'])
		palette.setColor(QPalette.WindowText,
			self.editor.palette().color(QPalette.WindowText))
		self.setPalette(palette)

	def mousePressEvent(self, event):
		pos = self.mapToParent(event.pos())
		pos.setX(pos.x() - self.editor.lineNumberAreaWidth())
		newEvent = QMouseEvent(event.type(), pos,
		                       event.button(), event.buttons(),
		                       event.modifiers())
		self.editor.mousePressEvent(newEvent)

	mouseReleaseEvent = mousePressEvent
	mouseDoubleClickEvent = mousePressEvent
	mouseMoveEvent = mousePressEvent
