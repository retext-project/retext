# This file is part of ReText
# Copyright: Dmitry Shachnev 2012-2014
# License: GNU GPL v2 or higher

from ReText import globalSettings, DOCTYPE_NONE, DOCTYPE_MARKDOWN, \
 DOCTYPE_REST, DOCTYPE_HTML
import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

reHtmlTags     = re.compile('<[^<>@]*>')
reHtmlSymbols  = re.compile('&[^; ]*;')
reHtmlStrings  = re.compile('"[^"<]*"(?=[^<]*>)')
reHtmlComments = re.compile('<!--[^<>]*-->')
reItalics1     = re.compile(r'(?<!\*)\*[^ \*][^\*]*\*')
reItalics2     = re.compile(r'(?<!_|\w)_[^_]+_(?!\w)')
reBold1        = re.compile(r'(?<!\*)\*\*((?!\*\*).)*\*\*')
reBold2        = re.compile(r'(?<!_|\w)__[^_]+__(?!\w)')
reBoldItalics1 = re.compile(r'\*{3,3}[^\*]+\*{3,3}')
reBoldItalics2 = re.compile('___[^_]+___')
reMkdHeaders   = re.compile('^#.+')
reMkdLinksImgs = re.compile(r'(?<=\[)[^\[\]]*(?=\])')
reMkdLinkRefs  = re.compile(r'(?<=\]\()[^\(\)]*(?=\))')
reBlockQuotes  = re.compile('^ *>.+')
reReSTDirects  = re.compile(r'\.\. [a-z]+::')
reReSTRoles    = re.compile(':[a-z]+:')
reWords        = re.compile('[^_\\W]+', flags=re.UNICODE)

colorNames = ('htmltags', 'htmlsymbols', 'htmlquotes', 'htmlcomments',
              'markdownlinks', 'blockquotes',
              'restdirectives', 'restroles')

defaultColorScheme = (
	Qt.darkMagenta,  # HTML tags
	Qt.darkCyan,     # HTML symbols
	Qt.darkYellow,   # HTML Quotes symbols inside tags
	Qt.gray,         # HTML comments
	Qt.blue,         # Markdown links and images
	Qt.darkGray,     # Blockquotes
	Qt.darkMagenta,  # reStructuredText directives
	Qt.darkRed,      # reStructuredText roles
)

colorScheme = defaultColorScheme
colorSchemeFile = None

def readColorSchemeFromFile(filename):
	colors = {}
	schemefile = open(filename)
	for line in schemefile:
		parts = line.split('=')
		if len(parts) == 2:
			colors[parts[0].rstrip()] = QColor(parts[1].strip())
	schemefile.close()
	return [colors[colorname] if colorname in colors
	        else defaultColorScheme[index]
	        for index, colorname in enumerate(colorNames)]

def updateColorScheme():
	global colorScheme
	newSchemeFile = globalSettings.colorSchemeFile
	if newSchemeFile and newSchemeFile != colorSchemeFile:
		colorScheme = readColorSchemeFromFile(newSchemeFile)
	if not newSchemeFile:
		colorScheme = defaultColorScheme

class ReTextHighlighter(QSyntaxHighlighter):
	dictionary = None
	docType = DOCTYPE_NONE

	def __init__(self, document):
		QSyntaxHighlighter.__init__(self, document)
		updateColorScheme()

	def highlightBlock(self, text):
		patterns = (
			# regex,         color,          font style,    italic, underline
			(reHtmlTags,     colorScheme[0], QFont.Bold),
			(reHtmlSymbols,  colorScheme[1], QFont.Bold),
			(reHtmlStrings,  colorScheme[2], QFont.Bold),
			(reHtmlComments, colorScheme[3], QFont.Normal),
			(reItalics1,     None,           QFont.Normal,  True),
			(reItalics2,     None,           QFont.Normal,  True),
			(reBold1,        None,           QFont.Bold),
			(reBold2,        None,           QFont.Bold),
			(reBoldItalics1, None,           QFont.Bold,    True),
			(reBoldItalics2, None,           QFont.Bold,    True),
			(reMkdHeaders,   None,           QFont.Black),
			(reMkdLinksImgs, colorScheme[4], QFont.Normal),
			(reMkdLinkRefs,  None,           QFont.Normal,  True,   True),
			(reBlockQuotes,  colorScheme[5], QFont.Normal),
			(reReSTDirects,  colorScheme[6], QFont.Normal),
			(reReSTRoles,    colorScheme[7], QFont.Normal)
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
				for match in pattern[0].finditer(text):
					self.setFormat(match.start(), match.end() - match.start(), charFormat)
		# Spell checker
		if self.dictionary:
			charFormat = QTextCharFormat()
			charFormat.setUnderlineColor(Qt.red)
			charFormat.setUnderlineStyle(QTextCharFormat.SpellCheckUnderline)
			for match in reWords.finditer(text):
				finalFormat = QTextCharFormat()
				finalFormat.merge(charFormat)
				finalFormat.merge(self.format(match.start()))
				if not self.dictionary.check(match.group(0)):
					self.setFormat(match.start(), match.end() - match.start(), finalFormat)
