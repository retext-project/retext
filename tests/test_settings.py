# This file is part of ReText
# Copyright: 2014-2024 Dmitry Shachnev
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

import sys
import tempfile
import unittest
from os.path import basename, dirname, splitext

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import QApplication

from ReText import (
    readFromSettings,
    readListFromSettings,
    writeListToSettings,
    writeToSettings,
)
from ReText.editor import getColor, updateColorScheme

# For this particular test, QCoreApplication is enough. However, we should
# only have one QCoreApplication instance for all tests in a process. As
# other tests need QApplication, we should not create a bare QCoreApplication
# here. Also, keep a reference so it is not garbage collected.
QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication.instance() or QApplication(sys.argv)

class TestSettings(unittest.TestCase):
    def setUp(self):
        self.tempFile = tempfile.NamedTemporaryFile(prefix='retext-', suffix='.ini')
        baseName = splitext(basename(self.tempFile.name))[0]
        QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                          dirname(self.tempFile.name))
        self.settings = QSettings(QSettings.Format.IniFormat,
                                  QSettings.Scope.UserScope, baseName)

    def tearDown(self):
        del self.settings # this should be deleted before tempFile
        self.tempFile.close()

    def test_storingLists(self):
        data = (
            ['1', '2', '3', 'test'],
            [],
            ['1'],
            ['true'],
            ['foo, bar', 'foo, bar']
        )
        for lst in data:
            writeListToSettings('testList', lst, self.settings)
            lnew = readListFromSettings('testList', self.settings)
            self.assertListEqual(lnew, lst)

    def test_storingBooleans(self):
        writeToSettings('testBool', 1, None, self.settings)
        self.assertTrue(readFromSettings('testBool', bool, self.settings))
        writeToSettings('testBool', 'false', None, self.settings)
        self.assertFalse(readFromSettings('testBool', bool, self.settings))
        writeToSettings('testBool', 0, None, self.settings)
        self.assertFalse(readFromSettings('testBool', bool, self.settings))

    def test_storingColors(self):
        self.settings.setValue('ColorScheme/htmlTags', 'green')
        self.settings.setValue('ColorScheme/htmlSymbols', '#ff8800')
        self.settings.setValue('ColorScheme/htmlComments', '#abc')
        updateColorScheme(self.settings)
        self.assertEqual(getColor('htmlTags'), QColor(0x00, 0x80, 0x00))
        self.assertEqual(getColor('htmlSymbols'), QColor(0xff, 0x88, 0x00))
        self.assertEqual(getColor('htmlStrings'), Qt.GlobalColor.darkYellow) # default
        self.assertEqual(getColor('htmlComments'), QColor(0xaa, 0xbb, 0xcc))

if __name__ == '__main__':
    unittest.main()
