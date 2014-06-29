# This file is part of ReText
# Copyright: Dmitry Shachnev 2014
# License: GNU GPL v2 or higher

import unittest
import tempfile

from os.path import basename, dirname, splitext
from PyQt5.QtCore import QSettings
from ReText import readListFromSettings, writeListToSettings, \
 readFromSettings, writeToSettings

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

if __name__ == '__main__':
	unittest.main()
