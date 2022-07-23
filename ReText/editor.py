# vim: ts=8:sts=8:sw=8:noexpandtab
#
# This file is part of ReText
# Copyright: 2012-2022 Dmitry Shachnev
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
from ReText import globalSettings, settings, tablemode

from PyQt6.QtCore import pyqtSignal, QFileInfo, QPoint, QRect, QSize, Qt
from PyQt6.QtGui import QAction, QColor, QImage, QKeyEvent, QMouseEvent, QPainter, \
QPalette, QTextCursor, QTextFormat, QWheelEvent, QGuiApplication
from PyQt6.QtWidgets import QApplication, QFileDialog, QLabel, QTextEdit, QWidget

try:
	from ReText.fakevimeditor import ReTextFakeVimHandler
except ImportError:
	ReTextFakeVimHandler = None

colors = {
	# Editor
	'marginLine':           {'light': '#dcd2dc', 'dark': '#3daee9'},
	'currentLineHighlight': {'light': '#ffffc8', 'dark': '#31363b'},
	'infoArea':             {'light': '#aaaaff55', 'dark': '#aa557f2a'},
	'statsArea':            {'light': '#aaffaa55', 'dark': '#aa7f552a'},
	'lineNumberArea':       {'light': '#00ffff', 'dark': '#31363b'},
	'lineNumberAreaText':   {'light': '#008080', 'dark': '#bdc3c7'},
	# Highlighter
	'htmlTags':             {'light': '#800080', 'dark': '#d070d0'},
	'htmlSymbols':          {'light': '#008080', 'dark': '#70d0a0'},
	'htmlStrings':          {'light': '#808000', 'dark': '#d0d070'},
	'htmlComments':         {'light': '#a0a0a4', 'dark': '#b0b0aa'},
	'codeSpans':            {'light': '#505050', 'dark': '#afafaf'},
	'markdownLinks':        {'light': '#000090', 'dark': '#8080ff'},
	'blockquotes':          {'light': '#808080', 'dark': '#b0b0b0'},
	'restDirectives':       {'light': '#800080', 'dark': '#d070d0'},
	'restRoles':            {'light': '#800000', 'dark': '#d07070'},
	'whitespaceOnEnd':      {'light': '#80e1e1a5', 'dark': '#8096966e'},
}

colorValues = {}

def updateColorScheme(settings=settings):
	palette = QApplication.palette()
	windowColor = palette.color(QPalette.ColorRole.Window)
	themeVariant = 'light' if windowColor.lightness() > 150 else 'dark'
	settings.beginGroup('ColorScheme')
	for key in colors:
		if settings.contains(key):
			colorValues[key] = settings.value(key, type=QColor)
		else:
			colorValues[key] = QColor(colors[key][themeVariant])
	settings.endGroup()

def getColor(colorName):
	if not colorValues:
		updateColorScheme()
	return colorValues[colorName]

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
	returnBlockPattern = re.compile("^[\\s]*([*>-]|\\d+\\.) ")
	orderedListPattern = re.compile("^([\\s]*)(\\d+)\\. $")
	wordPattern = re.compile(r"\w+")
	nonAlphaNumPattern = re.compile(r"\W")
	surroundKeysSelfClose = [
		Qt.Key.Key_Underscore,
		Qt.Key.Key_Asterisk,
		Qt.Key.Key_QuoteDbl,
		Qt.Key.Key_QuoteLeft,
		Qt.Key.Key_Apostrophe
	]
	surroundKeysOtherClose = {
		Qt.Key.Key_ParenLeft: ')',
		Qt.Key.Key_BracketLeft: ']'
	}

	def __init__(self, parent, settings=globalSettings):
		QTextEdit.__init__(self)
		self.tab = weakref.proxy(parent)
		self.parent = parent.p
		self.undoRedoActive = False
		self.tableModeEnabled = False
		self.setAcceptRichText(False)
		self.lineNumberArea = LineNumberArea(self)
		self.infoArea = LineInfoArea(self)
		self.statistics = (0, 0, 0)
		self.statsArea = TextInfoArea(self)
		self.updateFont()
		self.setWrapModeAndWidth()
		self.document().blockCountChanged.connect(self.updateLineNumberAreaWidth)
		self.cursorPositionChanged.connect(self.highlightCurrentLine)
		self.document().contentsChange.connect(self.contentsChange)
		self.settings = settings
		if globalSettings.useFakeVim:
			self.installFakeVimHandler()

	def setWrapModeAndWidth(self):
		if globalSettings.rightMarginWrap and (self.rect().topRight().x() > self.marginx):
			self.setLineWrapMode(QTextEdit.LineWrapMode.FixedPixelWidth)
			self.setLineWrapColumnOrWidth(self.marginx)
		else:
			self.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)

	def updateFont(self):
		self.setFont(globalSettings.getEditorFont())
		metrics = self.fontMetrics()
		self.marginx = (int(self.document().documentMargin())
			+ metrics.horizontalAdvance(' ' * globalSettings.rightMargin))
		self.setTabStopDistance(globalSettings.tabWidth * metrics.horizontalAdvance(' '))
		self.updateLineNumberAreaWidth()
		self.infoArea.updateTextAndGeometry()
		self.updateTextStatistics()
		self.statsArea.updateTextAndGeometry()
		if globalSettings.wideCursor:
			self.setCursorWidth(metrics.averageCharWidth())

	def paintEvent(self, event):
		if not globalSettings.rightMargin:
			return super().paintEvent(event)
		painter = QPainter(self.viewport())
		painter.setPen(getColor('marginLine'))
		y1 = self.rect().topLeft().y()
		y2 = self.rect().bottomLeft().y()
		painter.drawLine(self.marginx, y1, self.marginx, y2)
		super().paintEvent(event)

	def wheelEvent(self, event):
		modifiers = QGuiApplication.keyboardModifiers()
		if modifiers == Qt.KeyboardModifier.ControlModifier:
			font = globalSettings.getEditorFont()
			size = font.pointSize()
			scroll = event.angleDelta().y()
			if scroll > 0:
				size += 1
			elif scroll < 0:
				size -= 1
			else:
				return
			font.setPointSize(size)
			self.parent.setEditorFont(font)
		else:
			super().wheelEvent(event)

			if event.angleDelta().y() < 0:
				scrollBarLimit = self.verticalScrollBar().maximum()
			else:
				scrollBarLimit = self.verticalScrollBar().minimum()

			if self.verticalScrollBar().value() == scrollBarLimit:
				self.scrollLimitReached.emit(event)

	def scrollContentsBy(self, dx, dy):
		super().scrollContentsBy(dx, dy)
		self.lineNumberArea.update()

	def contextMenuEvent(self, event):
		# Create base menu
		menu = self.createStandardContextMenu()
		if self.parent.actionPasteImage.isEnabled():
			actions = menu.actions()
			actionPaste = menu.findChild(QAction, "edit-paste")
			actionNextAfterPaste = actions[actions.index(actionPaste) + 1]
			menu.insertAction(actionNextAfterPaste, self.parent.actionPasteImage)

		text = self.toPlainText()
		if not text:
			menu.exec(event.globalPos())
			return

		# Check word under the cursor
		oldcursor = self.textCursor()
		cursor = self.cursorForPosition(event.pos())
		curchar = self.document().characterAt(cursor.position())
		isalpha = curchar.isalpha()
		word = None
		if isalpha and not (oldcursor.hasSelection() and oldcursor.selectedText() != cursor.selectedText()):
			cursor.select(QTextCursor.SelectionType.WordUnderCursor)
			word = cursor.selectedText()

		correct = True
		if word is not None and self.tab.highlighter.dictionaries:
			correct = any(dictionary.check(word) for dictionary in self.tab.highlighter.dictionaries)

		if not correct:
			self.setTextCursor(cursor)
			suggestions = self.tab.highlighter.dictionaries[0].suggest(word)
			actions = [self.parent.act(sug, trig=self.fixWord(sug)) for sug in suggestions]
			menu.insertSeparator(menu.actions()[0])
			for action in actions[::-1]:
				menu.insertAction(menu.actions()[0], action)
			menu.insertSeparator(menu.actions()[0])
			menu.insertAction(menu.actions()[0], self.parent.act(self.tr('Add to dictionary'), trig=self.learnWord(word)))

		menu.addSeparator()
		menu.addAction(self.parent.actionMoveUp)
		menu.addAction(self.parent.actionMoveDown)

		menu.exec(event.globalPos())

	def fixWord(self, correctword):
		return lambda: self.insertPlainText(correctword)

	def learnWord(self, newword):
		return lambda: self.addNewWord(newword)

	def addNewWord(self, newword):
		cursor = self.textCursor()
		block = cursor.block()
		cursor.clearSelection()
		self.setTextCursor(cursor)
		if self.tab.highlighter.dictionaries and newword:
			dictionary = self.tab.highlighter.dictionaries[0]
			dictionary.add(newword)
			self.tab.highlighter.rehighlightBlock(block)

	def isSurroundKey(self, key):
		return key in self.surroundKeysSelfClose or key in self.surroundKeysOtherClose

	def getCloseKey(self, event, key):
		if key in self.surroundKeysSelfClose:
			return event.text()

		if key in self.surroundKeysOtherClose:
			return self.surroundKeysOtherClose[key]

	def surroundText(self, cursor, event, key):
		text = cursor.selectedText()
		keyStr = event.text()
		keyClose = self.getCloseKey(event, key)

		cursor.insertText(keyStr + text + keyClose)

	def keyPressEvent(self, event):
		key = event.key()
		cursor = self.textCursor()
		if key == Qt.Key.Key_Backspace and event.modifiers() & Qt.KeyboardModifier.GroupSwitchModifier:
			# Workaround for https://bugreports.qt.io/browse/QTBUG-49771
			event = QKeyEvent(event.type(), event.key(),
				event.modifiers() ^ Qt.KeyboardModifier.GroupSwitchModifier)
		if key == Qt.Key.Key_Tab:
			documentIndentMore(self.document(), cursor)
		elif key == Qt.Key.Key_Backtab:
			documentIndentLess(self.document(), cursor)
		elif key == Qt.Key.Key_Return:
			markupClass = self.tab.getActiveMarkupClass()
			if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
				cursor.insertText('\n')
				self.ensureCursorVisible()
			elif self.tableModeEnabled and tablemode.handleReturn(cursor, markupClass,
					newRow=(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)):
				self.setTextCursor(cursor)
				self.ensureCursorVisible()
			else:
				if event.modifiers() & Qt.KeyboardModifier.ShiftModifier and markupClass == MarkdownMarkup:
					# Insert Markdown-style line break
					cursor.insertText('  ')
				self.handleReturn(cursor)
		elif cursor.selectedText() and self.isSurroundKey(key):
			self.surroundText(cursor, event, key)
		else:
			if event.text() and self.tableModeEnabled:
				cursor.beginEditBlock()
			super().keyPressEvent(event)
			if event.text() and self.tableModeEnabled:
				cursor.endEditBlock()

	def handleReturn(self, cursor):
		# Select text between the cursor and the line start
		cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.KeepAnchor)
		text = cursor.selectedText()
		length = len(text)
		match = self.returnBlockPattern.search(text)
		if match is not None:
			matchedText = match.group(0)
			if len(matchedText) == length:
				cursor.removeSelectedText()
				matchedText = ''
			else:
				matchOL = self.orderedListPattern.match(matchedText)
				if matchOL is not None:
					matchedPrefix = matchOL.group(1)
					matchedNumber = int(matchOL.group(2))
					nextNumber = matchedNumber if self.settings.orderedListMode == 'repeat' else matchedNumber + 1
					matchedText = matchedPrefix + str(nextNumber) + ". "
		else:
			matchedText = ''
		# Reset the cursor
		cursor = self.textCursor()
		cursor.insertText('\n' + matchedText)
		self.ensureCursorVisible()

	def moveLineUp(self):
		self.moveLine(QTextCursor.MoveOperation.PreviousBlock)

	def moveLineDown(self):
		self.moveLine(QTextCursor.MoveOperation.NextBlock)

	def moveLine(self, direction):
		cursor = self.textCursor()
		# Select the current block
		cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock, QTextCursor.MoveMode.MoveAnchor)
		cursor.movePosition(QTextCursor.MoveOperation.NextBlock, QTextCursor.MoveMode.KeepAnchor)
		text = cursor.selectedText()
		# Remove it
		cursor.removeSelectedText()
		# Move to the wanted block
		cursor.movePosition(direction, QTextCursor.MoveMode.MoveAnchor)
		# Paste the line
		cursor.insertText(text)
		# Move to the pasted block
		cursor.movePosition(QTextCursor.MoveOperation.PreviousBlock, QTextCursor.MoveMode.MoveAnchor)
		# Update cursor
		self.setTextCursor(cursor)

	def lineNumberAreaWidth(self):
		if not globalSettings.lineNumbersEnabled:
			return 0
		cursor = QTextCursor(self.document())
		cursor.movePosition(QTextCursor.MoveOperation.End)
		if globalSettings.relativeLineNumbers:
			digits = len(str(cursor.blockNumber())) + 1
		else:
			digits = len(str(cursor.blockNumber() + 1))
		return 5 + self.fontMetrics().horizontalAdvance('9') * digits

	def updateLineNumberAreaWidth(self, blockcount=0):
		self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)

	def resizeEvent(self, event):
		super().resizeEvent(event)
		rect = self.contentsRect()
		self.resized.emit(rect)
		self.lineNumberArea.setGeometry(rect.left(), rect.top(),
			self.lineNumberAreaWidth(), rect.height())
		self.infoArea.updateTextAndGeometry()
		self.statsArea.updateTextAndGeometry()
		self.setWrapModeAndWidth()
		self.ensureCursorVisible()

	def highlightCurrentLine(self):
		if globalSettings.relativeLineNumbers:
			self.lineNumberArea.update()
		if globalSettings.highlightCurrentLine == 'disabled':
			return self.setExtraSelections([])
		selection = QTextEdit.ExtraSelection()
		selection.format.setBackground(getColor('currentLineHighlight'))
		selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
		selection.cursor = self.textCursor()
		selection.cursor.clearSelection()
		selections = [selection]
		if globalSettings.highlightCurrentLine == 'wrapped-line':
			selections.append(QTextEdit.ExtraSelection())
			selections[0].cursor.movePosition(QTextCursor.MoveOperation.StartOfBlock)
			selections[0].cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock, QTextCursor.MoveMode.KeepAnchor)
			selections[1].format.setBackground(getColor('currentLineHighlight'))
			selections[1].format.setProperty(QTextFormat.Property.FullWidthSelection, True)
			selections[1].cursor = self.textCursor()
			selections[1].cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
		elif selection.cursor.block().textDirection() == Qt.LayoutDirection.RightToLeft:
			# FullWidthSelection does not work correctly for RTL direction
			selection.cursor.movePosition(QTextCursor.MoveOperation.StartOfLine)
			selection.cursor.movePosition(QTextCursor.MoveOperation.EndOfLine, QTextCursor.MoveMode.KeepAnchor)
		self.setExtraSelections(selections)

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
		self.updateTextStatistics()

	def findNextImageName(self, filenames):
		highestNumber = 0
		for filename in filenames:
			m = re.match(r'image(\d+).png', filename, re.IGNORECASE)
			if m:
				number = int(m.group(1))
				highestNumber = max(number, highestNumber)
		return 'image%04d.png' % (highestNumber + 1)

	def getImageFilename(self):
		if self.tab.fileName:
			saveDir = os.path.dirname(self.tab.fileName)
		else:
			saveDir = os.getcwd()

		imageFileName = self.findNextImageName(os.listdir(saveDir))

		return QFileDialog.getSaveFileName(self,
		                                   self.tr('Save image'),
		                                   os.path.join(saveDir, imageFileName),
		                                   self.tr('Images (*.png *.jpg)'))[0]

	def makeFileNameRelative(self, fileName):
		"""Tries to make the given fileName relative. If the document is
		not saved, or the fileName is on a different root, returns the
		original fileName.
		"""
		if self.tab.fileName:
			currentDir = os.path.dirname(self.tab.fileName)
			try:
				return os.path.relpath(fileName, currentDir)
			except ValueError:  # different roots
				return fileName
		return fileName

	def getImageMarkup(self, fileName):
		"""Returns markup for image in the current markup language.

		This method is also accessed in ReTextWindow.insertImage.
		"""
		link = self.makeFileNameRelative(fileName)
		markupClass = self.tab.getActiveMarkupClass()
		if markupClass == MarkdownMarkup:
			return '![%s](%s)' % (QFileInfo(link).baseName(), link)
		elif markupClass == ReStructuredTextMarkup:
			return '.. image:: %s' % link
		elif markupClass == TextileMarkup:
			return '!%s!' % link

	def pasteImage(self):
		mimeData = QApplication.instance().clipboard().mimeData()
		fileName = self.getImageFilename()
		if not fileName or not mimeData.hasImage():
			return
		image = QImage(mimeData.imageData())
		image.save(fileName)

		imageText = self.getImageMarkup(fileName)

		self.textCursor().insertText(imageText)

	def installFakeVimHandler(self):
		if ReTextFakeVimHandler:
			fakeVimEditor = ReTextFakeVimHandler(self, self.parent)
			fakeVimEditor.setSaveAction(self.parent.actionSave)
			fakeVimEditor.setQuitAction(self.parent.actionQuit)
			self.parent.actionFakeVimMode.triggered.connect(fakeVimEditor.remove)

	def updateTextStatistics(self):
		if not globalSettings.documentStatsEnabled:
			return
		text = self.toPlainText()
		wordCount = len(self.wordPattern.findall(text))
		alphaNums = self.nonAlphaNumPattern.sub('', text)
		alphaNumCount = len(alphaNums)
		characterCount = len(text)
		self.statistics = (wordCount, alphaNumCount, characterCount)


class LineNumberArea(QWidget):
	def __init__(self, editor):
		QWidget.__init__(self, editor)
		self.editor = editor

	def sizeHint(self):
		return QSize(self.editor.lineNumberAreaWidth(), 0)

	def paintEvent(self, event):
		if not globalSettings.lineNumbersEnabled:
			return super().paintEvent(event)
		painter = QPainter(self)
		painter.fillRect(event.rect(), getColor('lineNumberArea'))
		painter.setPen(getColor('lineNumberAreaText'))
		cursor = self.editor.cursorForPosition(QPoint(0, 0))
		atEnd = False
		fontHeight = self.fontMetrics().height()
		height = self.editor.height()
		if globalSettings.relativeLineNumbers:
			relativeTo = self.editor.textCursor().blockNumber()
		else:
			relativeTo = -1
		while not atEnd:
			rect = self.editor.cursorRect(cursor)
			if rect.top() >= height:
				break
			number = str(cursor.blockNumber() - relativeTo).replace('-', '−')
			painter.drawText(0, rect.top(), self.width() - 2,
			                 fontHeight, Qt.AlignmentFlag.AlignRight, number)
			cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
			atEnd = cursor.atEnd()
			if not atEnd:
				cursor.movePosition(QTextCursor.MoveOperation.NextBlock)

class InfoArea(QLabel):
	def __init__(self, editor, baseColor):
		QWidget.__init__(self, editor)
		self.editor = editor
		self.editor.cursorPositionChanged.connect(self.updateTextAndGeometry)
		self.updateTextAndGeometry()
		self.setAutoFillBackground(True)
		self.baseColor = baseColor
		palette = self.palette()
		palette.setColor(QPalette.ColorRole.Window, self.baseColor)
		self.setPalette(palette)
		self.setCursor(Qt.CursorShape.IBeamCursor)

	def updateTextAndGeometry(self):
		text = self.getText()
		(w, h) = self.getAreaSize(text)
		(x, y) = self.getAreaPosition(w, h)
		self.setText(text)
		self.resize(w, h)
		self.move(x, y)
		self.setVisible(not globalSettings.useFakeVim)

	def getAreaSize(self, text):
		metrics = self.fontMetrics()
		width = metrics.horizontalAdvance(text)
		height = metrics.height()
		return width, height

	def getAreaPosition(self, width, height):
		return 0, 0

	def getText(self):
		return ""

	def enterEvent(self, event):
		palette = self.palette()
		windowColor = QColor(self.baseColor)
		windowColor.setAlpha(0x20)
		palette.setColor(QPalette.ColorRole.Window, windowColor)
		textColor = palette.color(QPalette.ColorRole.WindowText)
		textColor.setAlpha(0x20)
		palette.setColor(QPalette.ColorRole.WindowText, textColor)
		self.setPalette(palette)

	def leaveEvent(self, event):
		palette = self.palette()
		palette.setColor(QPalette.ColorRole.Window, self.baseColor)
		palette.setColor(QPalette.ColorRole.WindowText,
			self.editor.palette().color(QPalette.ColorRole.WindowText))
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

class LineInfoArea(InfoArea):
	def __init__(self, editor):
		InfoArea.__init__(self, editor, getColor('infoArea'))

	def getAreaPosition(self, width, height):
		viewport = self.editor.viewport()
		rightSide = viewport.width() + self.editor.lineNumberAreaWidth()
		if globalSettings.documentStatsEnabled:
			return rightSide - width, viewport.height() - (2 * height)
		else:
			return rightSide - width, viewport.height() - height

	def getText(self):
		template = '%d : %d'
		cursor = self.editor.textCursor()
		block = cursor.blockNumber() + 1
		position = cursor.positionInBlock()
		return template % (block, position)


class TextInfoArea(InfoArea):
	def __init__(self, editor):
		InfoArea.__init__(self, editor, getColor('statsArea'))

	def getAreaPosition(self, width, height):
		viewport = self.editor.viewport()
		rightSide = viewport.width() + self.editor.lineNumberAreaWidth()
		return rightSide - width, viewport.height() - height

	def getText(self):
		if not globalSettings.documentStatsEnabled:
			return
		template = self.tr('%d w | %d a | %d c',
		                   'count of words, alphanumeric characters, all characters')
		words, alphaNums, characters = self.editor.statistics
		return template % (words, alphaNums, characters)
