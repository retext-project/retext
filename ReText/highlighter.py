# This file is part of ReText
# Copyright: 2012-2015 Dmitry Shachnev
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

from ReText import settings
import re

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

reHtmlTags     = re.compile('<[^<>@]*>')
reHtmlSymbols  = re.compile(r'&#?\w+;')
reHtmlStrings  = re.compile('"[^"<]*"(?=[^<]*>)')
reHtmlComments = re.compile('<!--[^<>]*-->')
reAsterisks    = re.compile(r'(?<!\*)\*[^ \*][^\*]*\*')
reUnderline    = re.compile(r'(?<!_|\w)_[^_]+_(?!\w)')
reDblAsterisks = re.compile(r'(?<!\*)\*\*((?!\*\*).)*\*\*')
reDblUnderline = re.compile(r'(?<!_|\w)__[^_]+__(?!\w)')
reTrpAsterisks = re.compile(r'\*{3,3}[^\*]+\*{3,3}')
reTrpUnderline = re.compile('___[^_]+___')
reMkdHeaders   = re.compile('^#.+')
reMkdLinksImgs = re.compile(r'(?<=\[)[^\[\]]*(?=\])')
reMkdLinkRefs  = re.compile(r'(?<=\]\()[^\(\)]*(?=\))')
reBlockQuotes  = re.compile('^ *>.+')
reReSTDirects  = re.compile(r'\.\. [a-z]+::')
reReSTRoles    = re.compile(':[a-z]+:')
reTextileHdrs  = re.compile(r'^h[1-6][()<>=]*\.\s.+')
reTextileQuot  = re.compile(r'^bq\.\s.+')
reWords        = re.compile('[^_\\W]+', flags=re.UNICODE)
reSpacesOnEnd  = re.compile(r'\s+$', flags=re.UNICODE)

defaultColorScheme = {
	'htmlTags': Qt.darkMagenta,
	'htmlSymbols': Qt.darkCyan,
	'htmlStrings': Qt.darkYellow,
	'htmlComments': Qt.gray,
	'markdownLinks': Qt.blue,
	'blockquotes': Qt.darkGray,
	'restDirectives': Qt.darkMagenta,
	'restRoles': Qt.darkRed,
	'whitespaceOnEnd': QColor(0xe1, 0xe1, 0xa5, 0x80)
}
colorScheme = {}

def updateColorScheme(settings=settings):
	settings.beginGroup('ColorScheme')
	for key in defaultColorScheme:
		if settings.contains(key):
			colorScheme[key] = settings.value(key, type=QColor)
		else:
			colorScheme[key] = defaultColorScheme[key]
	settings.endGroup()

updateColorScheme()

class ReTextHighlighter(QSyntaxHighlighter):
	dictionary = None
	docType = None

	def highlightBlock(self, text):
		patterns = (
			# regex,         color,            font style,    italic, underline
			(reHtmlTags,     'htmlTags',       QFont.Bold),                     # 0
			(reHtmlSymbols,  'htmlSymbols',    QFont.Bold),                     # 1
			(reHtmlStrings,  'htmlStrings',    QFont.Bold),                     # 2
			(reHtmlComments, 'htmlComments',   QFont.Normal),                   # 3
			(reAsterisks,    None,             QFont.Normal,  True),            # 4
			(reUnderline,    None,             QFont.Normal,  True),            # 5
			(reDblAsterisks, None,             QFont.Bold),                     # 6
			(reDblUnderline, None,             QFont.Bold),                     # 7
			(reTrpAsterisks, None,             QFont.Bold,    True),            # 8
			(reTrpUnderline, None,             QFont.Bold,    True),            # 9
			(reMkdHeaders,   None,             QFont.Black),                    # 10
			(reMkdLinksImgs, 'markdownLinks',  QFont.Normal),                   # 11
			(reMkdLinkRefs,  None,             QFont.Normal,  True,   True),    # 12
			(reBlockQuotes,  'blockquotes',    QFont.Normal),                   # 13
			(reReSTDirects,  'restDirectives', QFont.Bold),                     # 14
			(reReSTRoles,    'restRoles',      QFont.Bold),                     # 15
			(reTextileHdrs,  None,             QFont.Black),                    # 16
			(reTextileQuot,  'blockquotes',    QFont.Normal),                   # 17
			(reAsterisks,    None,             QFont.Bold),                     # 18
			(reDblUnderline, None,             QFont.Normal,  True),            # 19
		)
		patternsDict = {
			'Markdown': (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13),
			'reStructuredText': (4, 6, 14, 15),
			'Textile': (0, 5, 6, 16, 17, 18, 19),
			'html': (0, 1, 2, 3)
		}
		# Syntax highlighter
		if self.docType in patternsDict:
			for number in patternsDict[self.docType]:
				pattern = patterns[number]
				charFormat = QTextCharFormat()
				charFormat.setFontWeight(pattern[2])
				if pattern[1] != None:
					charFormat.setForeground(colorScheme[pattern[1]])
				if len(pattern) >= 4:
					charFormat.setFontItalic(pattern[3])
				if len(pattern) >= 5:
					charFormat.setFontUnderline(pattern[4])
				for match in pattern[0].finditer(text):
					self.setFormat(match.start(), match.end() - match.start(), charFormat)
		for match in reSpacesOnEnd.finditer(text):
			charFormat = QTextCharFormat()
			charFormat.setBackground(colorScheme['whitespaceOnEnd'])
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
