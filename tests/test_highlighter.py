# This file is part of ReText
# Copyright: 2014 Dmitry Shachnev
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
