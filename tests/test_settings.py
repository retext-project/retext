# This file is part of ReText
# Copyright: 2014-2015 Dmitry Shachnev
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
import tempfile
import sys

from os.path import basename, dirname, splitext
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtWidgets import QApplication
from ReText import readListFromSettings, writeListToSettings, \
 readFromSettings, writeToSettings
from ReText.highlighter import colorScheme, updateColorScheme

# For this particular test, QCoreApplication is enough. However, we should
# only have one QCoreApplication instance for all tests in a process. As
# other tests need QApplication, we should not create a bare QCoreApplication
# here. Also, keep a reference so it is not garbage collected.
if hasattr(Qt, 'AA_ShareOpenGLContexts'):
	QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
app = QApplication.instance() or QApplication(sys.argv)

class TestSettings(unittest.TestCase):
	def setUp(self):
		self.tempFile = tempfile.NamedTemporaryFile(prefix='retext-', suffix='.ini')
		baseName = splitext(basename(self.tempFile.name))[0]
		QSettings.setPath(QSettings.IniFormat, QSettings.UserScope,
		                  dirname(self.tempFile.name))
		self.settings = QSettings(QSettings.IniFormat,
		                          QSettings.UserScope, baseName)

	def tearDown(self):
		del self.settings # this should be deleted before tempFile

	def test_storingLists(self):
		data = (
			['1', '2', '3', 'test'],
			[],
			['1'],
			['true'],
			['foo, bar', 'foo, bar']
		)
		for l in data:
			writeListToSettings('testList', l, self.settings)
			lnew = readListFromSettings('testList', self.settings)
			self.assertListEqual(lnew, l)

	def test_storingBooleans(self):
		writeToSettings('testBool', 1, None, self.settings)
		self.assertTrue(readFromSettings('testBool', bool, self.settings))
		writeToSettings('testBool', 'false', None, self.settings)
		self.assertFalse(readFromSettings('testBool', bool, self.settings))
		writeToSettings('testBool', 0, None, self.settings)
		self.assertFalse(readFromSettings('testBool', bool, self.settings))

	def test_storingFonts(self):
		font = QFont()
		font.setFamily('my family')
		font.setPointSize(20)
		writeToSettings('testFont', font, None, self.settings)
		family = readFromSettings('testFont', str, self.settings)
		size = readFromSettings('testFontSize', int, self.settings)
		self.assertEqual(family, 'my family')
		self.assertEqual(size, 20)
		newFont = readFromSettings('testFont', QFont, self.settings, QFont())
		self.assertEqual(newFont.family(), family)
		self.assertEqual(newFont.pointSize(), size)

	def test_storingColors(self):
		self.settings.setValue('ColorScheme/htmlTags', 'green')
		self.settings.setValue('ColorScheme/htmlSymbols', '#ff8800')
		self.settings.setValue('ColorScheme/htmlComments', '#abc')
		updateColorScheme(self.settings)
		self.assertEqual(colorScheme['htmlTags'], QColor(0x00, 0x80, 0x00))
		self.assertEqual(colorScheme['htmlSymbols'], QColor(0xff, 0x88, 0x00))
		self.assertEqual(colorScheme['htmlStrings'], Qt.darkYellow) # default
		self.assertEqual(colorScheme['htmlComments'], QColor(0xaa, 0xbb, 0xcc))

if __name__ == '__main__':
	unittest.main()
