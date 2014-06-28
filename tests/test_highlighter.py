# This file is part of ReText
# Copyright: Dmitry Shachnev 2014
# License: GNU GPL v2 or higher

import unittest
from PyQt5.QtCore import Qt, QTemporaryFile, QTextStream
from PyQt5.QtGui import QColor
from ReText.highlighter import readColorSchemeFromFile

class TestHighlighter(unittest.TestCase):
	def test_readColorSchemeFromFile(self):
		tempFile = QTemporaryFile('XXXXXX.colorscheme')
		tempFile.open(QTemporaryFile.WriteOnly)
		stream = QTextStream(tempFile)
		stream << 'htmltags = green\n'
		stream << 'htmlsymbols=#ff8800\n'
		stream << 'foo bar\n'
		stream << 'htmlcomments = #abc\n'
		tempFile.close()
		fileName = tempFile.fileName()
		colorScheme = readColorSchemeFromFile(fileName)
		self.assertEqual(colorScheme[0], QColor(0x00, 0x80, 0x00))
		self.assertEqual(colorScheme[1], QColor(0xff, 0x88, 0x00))
		self.assertEqual(colorScheme[2], Qt.darkYellow) # default
		self.assertEqual(colorScheme[3], QColor(0xaa, 0xbb, 0xcc))

if __name__ == '__main__':
	unittest.main()
