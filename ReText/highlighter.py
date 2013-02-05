# This file is part of ReText
# Copyright: Dmitry Shachnev 2012
# License: GNU GPL v2 or higher

from ReText import *
import re

def isHeaderLine(text):
	if len(text) < 3:
		return False
	return (text[0] in '=-*~^+') and (text == text[0] * len(text))

def isHeader(block):
	prevText = block.previous().text()
	if prevText and not isHeaderLine(prevText):
		return False
	return block.text() and isHeaderLine(block.next().text())

def isPartOfHeader(block):
	return isHeader(block) or isHeader(block.next()) or isHeader(block.previous())

def isHighlighted(block):
	cursor = QTextCursor(block)
	cursor.select(QTextCursor.BlockUnderCursor)
	return (cursor.charFormat().fontWeight() == QFont.Black)

class ReTextHighlighter(QSyntaxHighlighter):
	dictionary = None
	docType = DOCTYPE_NONE
	
	def highlightBlock(self, text):
		patterns = (
			('<[^<>@]*>', Qt.darkMagenta, QFont.Bold),         # 0: HTML tags
			('&[^; ]*;', Qt.darkCyan, QFont.Bold),             # 1: HTML symbols
			('"[^"<]*"(?=[^<]*>)', Qt.darkYellow, QFont.Bold), # 2: Quoted strings inside tags
			('<!--[^<>]*-->', Qt.gray, QFont.Normal),          # 3: HTML comments
			(r'(?<!\*)\*[^ \*][^\*]*\*', None, QFont.Normal, True), # 4: *Italics*
			(r'(?<!_|\w)_[^_]+_(?!\w)', None, QFont.Normal, True),  # 5: _Italics_
			(r'(?<!\*)\*\*((?!\*\*).)*\*\*', None, QFont.Bold), # 6: **Bold**
			(r'(?<!_|\w)__[^_]+__(?!\w)', None, QFont.Bold),   # 7: __Bold__
			(r'\*{3,3}[^\*]+\*{3,3}', None, QFont.Bold, True), # 8: ***BoldItalics***
			('___[^_]+___', None, QFont.Bold, True),           # 9: ___BoldItalics___
			('^#.+', None, QFont.Black),                       # 10: Headers
			(r'(?<=\[)[^\[\]]*(?=\])', Qt.blue, QFont.Normal), # 11: Links and images
			(r'(?<=\]\()[^\(\)]*(?=\))', None, QFont.Normal, True, True), # 12: Link references
			('^ *>.+', Qt.darkGray, QFont.Normal),             # 13: Blockquotes
			('.. [a-z]+::', Qt.darkMagenta, QFont.Normal),     # 14: reStructuredText directives
			(':[a-z]+:', Qt.darkRed, QFont.Normal)             # 15: reStructuredText roles
		)
		patternsDict = {
			DOCTYPE_NONE: (),
			DOCTYPE_MARKDOWN: (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13),
			DOCTYPE_REST: (4, 6, 14, 15),
			DOCTYPE_HTML: (0, 1, 2, 3)
		}
		# Syntax highlighter
		if self.docType in patternsDict:
			for number in patternsDict[self.docType]:
				pattern = patterns[number]
				charFormat = QTextCharFormat()
				charFormat.setFontWeight(pattern[2])
				if pattern[1] != None:
					charFormat.setForeground(pattern[1])
				if len(pattern) >= 4:
					charFormat.setFontItalic(pattern[3])
				if len(pattern) >= 5:
					charFormat.setFontUnderline(pattern[4])
				for match in re.finditer(pattern[0], text):
					self.setFormat(match.start(), match.end() - match.start(), charFormat)
		# Headers highlighter
		curBlock = self.currentBlock()
		if isHeaderLine(curBlock.text()):
			charFormat = QTextCharFormat()
			charFormat.setFontWeight(QFont.Black)
			for block in (curBlock.previous(), curBlock.next()):
				if isHeader(block):
					for bl in (block, block.previous(), block.next()):
						cursor = QTextCursor(bl)
						cursor.select(QTextCursor.BlockUnderCursor)
						cursor.mergeCharFormat(charFormat)
		elif isHighlighted(curBlock):
			while curBlock.blockNumber() and isHighlighted(curBlock.previous()):
				curBlock = curBlock.previous()
			for bl in (curBlock, curBlock.next(), curBlock.next().next()):
				if not isPartOfHeader(bl):
					# Undo the header formatting
					cursor = QTextCursor(bl)
					cursor.select(QTextCursor.BlockUnderCursor)
					charFormat = QTextCharFormat()
					charFormat.setFontWeight(QFont.Normal)
					cursor.mergeCharFormat(charFormat)
		# Spell checker
		if self.dictionary:
			charFormat = QTextCharFormat()
			charFormat.setUnderlineColor(Qt.red)
			charFormat.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
			for match in re.finditer('[^_\\W]+', text, flags=re.UNICODE):
				finalFormat = QTextCharFormat()
				finalFormat.merge(charFormat)
				finalFormat.merge(self.format(match.start()))
				if not self.dictionary.check(match.group(0)):
					self.setFormat(match.start(), match.end() - match.start(), finalFormat)
