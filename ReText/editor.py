# This file is part of ReText
# Copyright: Dmitry Shachnev 2012
# License: GNU GPL v2 or higher

from ReText import QtCore, QtGui, QtWidgets, monofont, globalSettings, DOCTYPE_MARKDOWN

(QPoint, QSize, Qt) = (QtCore.QPoint, QtCore.QSize, QtCore.Qt)
(QColor, QPainter, QTextCursor, QTextFormat) = (QtGui.QColor, QtGui.QPainter,
 QtGui.QTextCursor, QtGui.QTextFormat)
(QTextEdit, QWidget) = (QtWidgets.QTextEdit, QtWidgets.QWidget)

class ReTextEdit(QTextEdit):
	def __init__(self, parent):
		QTextEdit.__init__(self)
		self.parent = parent
		self.setFont(monofont)
		self.setAcceptRichText(False)
		self.marginx = (self.cursorRect(self.cursorForPosition(QPoint())).topLeft().x()
			+ self.fontMetrics().width(" "*globalSettings.rightMargin))
		if globalSettings.lineNumbersEnabled:
			self.lineNumberArea = LineNumberArea(self)
			self.document().blockCountChanged.connect(self.updateLineNumberAreaWidth)
			self.updateLineNumberAreaWidth()
		self.cursorPositionChanged.connect(self.highlightCurrentLine)
	
	def paintEvent(self, event):
		if not globalSettings.rightMargin:
			return QTextEdit.paintEvent(self, event)
		painter = QPainter(self.viewport())
		painter.setPen(QColor(220, 210, 220))
		y1 = self.rect().topLeft().y()
		y2 = self.rect().bottomLeft().y()
		painter.drawLine(self.marginx, y1, self.marginx, y2)
		QTextEdit.paintEvent(self, event)
	
	def scrollContentsBy(self, dx, dy):
		QTextEdit.scrollContentsBy(self, dx, dy)
		if hasattr(self, 'lineNumberArea'):
			self.lineNumberArea.repaint()

	def lineNumberAreaPaintEvent(self, event):
		painter = QPainter(self.lineNumberArea)
		painter.fillRect(event.rect(), Qt.cyan)
		cursor = QTextCursor(self.document())
		cursor.movePosition(QTextCursor.Start)
		atEnd = False
		while not atEnd:
			rect = self.cursorRect(cursor)
			block = cursor.block()
			if block.isVisible():
				number = str(cursor.blockNumber() + 1)
				painter.setPen(Qt.darkCyan)
				painter.drawText(0, rect.top(), self.lineNumberArea.width()-2,
					self.fontMetrics().height(), Qt.AlignRight, number)
			cursor.movePosition(QTextCursor.EndOfBlock)
			atEnd = cursor.atEnd()
			if not atEnd:
				cursor.movePosition(QTextCursor.NextBlock)
	
	def getHighlighter(self):
		return self.parent.highlighters[self.parent.ind]
	
	def contextMenuEvent(self, event):
		text = self.toPlainText()
		dictionary = self.getHighlighter().dictionary
		if (dictionary is None) or not text:
			return QTextEdit.contextMenuEvent(self, event)
		oldcursor = self.textCursor()
		cursor = self.cursorForPosition(event.pos())
		pos = cursor.positionInBlock()
		if pos == len(text): pos -= 1
		curchar = text[pos]
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
		menu.exec_(event.globalPos())
	
	def fixWord(self, correctword):
		return lambda: self.insertPlainText(correctword)
	
	def keyPressEvent(self, event):
		key = event.key()
		cursor = self.textCursor()
		if key == Qt.Key_Tab:
			self.indentMore()
		elif key == Qt.Key_Backtab:
			self.indentLess()
		elif key == Qt.Key_Return and not cursor.hasSelection():
			if event.modifiers() & Qt.ShiftModifier:
				# Insert Markdown-style line break
				markupClass = self.parent.getMarkupClass()
				if markupClass and markupClass.name == DOCTYPE_MARKDOWN:
					cursor.insertText('  ')
			if event.modifiers() & Qt.ControlModifier:
				cursor.insertText('\n')
			else:
				self.handleReturn(cursor)
		else:
			QTextEdit.keyPressEvent(self, event)
	
	def handleReturn(self, cursor):
		# Select text between the cursor and the line start
		cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
		text = cursor.selectedText()
		length = len(text)
		pos = 0
		while pos < length and text[pos] in (' ', '\t'):
			pos += 1
		# Reset the cursor
		cursor = self.textCursor()
		cursor.insertText('\n'+text[:pos])
		self.ensureCursorVisible()
	
	def indentMore(self):
		cursor = self.textCursor()
		if cursor.hasSelection():
			block = self.document().findBlock(cursor.selectionStart())
			end = self.document().findBlock(cursor.selectionEnd()).next()
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
	
	def indentLess(self):
		cursor = self.textCursor()
		document = self.document()
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
	
	def lineNumberAreaWidth(self):
		cursor = QTextCursor(self.document())
		cursor.movePosition(QTextCursor.End)
		digits = len(str(cursor.blockNumber() + 1))
		return 5 + self.fontMetrics().width('9') * digits
	
	def updateLineNumberAreaWidth(self, blockcount=0):
		self.lineNumberArea.repaint()
		self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
	
	def resizeEvent(self, event):
		QTextEdit.resizeEvent(self, event)
		if not globalSettings.lineNumbersEnabled:
			return
		rect = self.contentsRect()
		self.lineNumberArea.setGeometry(rect.left(), rect.top(),
			self.lineNumberAreaWidth(), rect.height())
	
	def highlightCurrentLine(self):
		if not globalSettings.highlightCurrentLine:
			return self.setExtraSelections([])
		selection = QTextEdit.ExtraSelection();
		lineColor = QColor(255, 255, 200)
		selection.format.setBackground(lineColor)
		selection.format.setProperty(QTextFormat.FullWidthSelection, True)
		selection.cursor = self.textCursor()
		selection.cursor.clearSelection()
		self.setExtraSelections([selection])

class LineNumberArea(QWidget):
	def __init__(self, editor):
		QWidget.__init__(self, editor)
		self.editor = editor
	
	def sizeHint(self):
		return QSize(self.editor.lineNumberAreaWidth(), 0)
	
	def paintEvent(self, event):
		return self.editor.lineNumberAreaPaintEvent(event)
