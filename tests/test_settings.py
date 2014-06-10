# This file is part of ReText
# Copyright: Dmitry Shachnev 2014
# License: GNU GPL v2 or higher

import unittest

from PyQt5.QtCore import QSettings, QTemporaryFile
from ReText import readListFromSettings, writeListToSettings, \
 readFromSettings, writeToSettings

class TestSettings(unittest.TestCase):
	def setUp(self):
		tempFile = QTemporaryFile('settings-XXXXXX.ini')
		self.settings = QSettings(tempFile.fileName())

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
