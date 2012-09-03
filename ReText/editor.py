from ReText import *

class ReTextEdit(QTextEdit):
	def __init__(self, parent):
		QTextEdit.__init__(self)
		self.parent = parent
		self.setFont(monofont)
		self.setAcceptRichText(False)
		self.marginx = (self.cursorRect(self.cursorForPosition(QPoint())).topLeft().x()
			+ self.fontMetrics().width(" "*parent.rightMargin))
	
	def paintEvent(self, event):
		if not self.parent.rightMargin:
			return QTextEdit.paintEvent(self, event)
		painter = QPainter(self.viewport())
		painter.setPen(QColor(220, 210, 220))
		y1 = self.rect().topLeft().y()
		y2 = self.rect().bottomLeft().y()
		painter.drawLine(QLine(self.marginx, y1, self.marginx, y2))
		QTextEdit.paintEvent(self, event)
	
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
		try:
			curchar = text[pos]
			isalpha = curchar.isalpha()
		except AttributeError:
			# For Python 2
			curchar = text.at(pos)
			isalpha = curchar.isLetter()
		cursor.select(QTextCursor.WordUnderCursor)
		if not isalpha or (oldcursor.hasSelection() and
		oldcursor.selectedText() != cursor.selectedText()):
			return QTextEdit.contextMenuEvent(self, event)
		self.setTextCursor(cursor)
		word = convertToUnicode(cursor.selectedText())
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
			markdownLineBreak = False
			if event.modifiers() & Qt.ShiftModifier:
				# Markdown-style line break
				markupClass = self.parent.getMarkupClass()
				if markupClass and markupClass.name == DOCTYPE_MARKDOWN:
					markdownLineBreak = True
			if event.modifiers() & Qt.ControlModifier:
				if markdownLineBreak:
					cursor.insertText('  ')
				cursor.insertText('\n')
			else:
				self.handleReturn(cursor, markdownLineBreak)
		else:
			QTextEdit.keyPressEvent(self, event)
	
	def handleReturn(self, cursor, markdownLineBreak):
		# Select text between the cursor and the line start
		cursor.movePosition(QTextCursor.StartOfLine, QTextCursor.KeepAnchor)
		text = convertToUnicode(cursor.selectedText())
		length = len(text)
		pos = 0
		while pos < length and text[pos] in (' ', '\t'):
			pos += 1
		# Reset the cursor
		cursor = self.textCursor()
		if markdownLineBreak:
			cursor.insertText('  ')
		cursor.insertText('\n'+text[:pos])
	
	def indentMore(self):
		cursor = self.textCursor()
		if cursor.hasSelection():
			block = self.document().findBlock(cursor.selectionStart())
			end = self.document().findBlock(cursor.selectionEnd()).next()
			cursor.beginEditBlock()
			while block != end:
				cursor.setPosition(block.position())
				if self.parent.tabInsertsSpaces:
					cursor.insertText(' ' * self.parent.tabWidth)
				else:
					cursor.insertText('\t')
				block = block.next()
			cursor.endEditBlock()
		else:
			indent = self.parent.tabWidth - (cursor.positionInBlock()
				% self.parent.tabWidth)
			if self.parent.tabInsertsSpaces:
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
				and pos < self.parent.tabWidth:
					pos += 1
					cursor.deleteChar()
			block = block.next()
		cursor.endEditBlock()
