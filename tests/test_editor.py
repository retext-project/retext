# This file is part of ReText
# Copyright: Dmitry Shachnev 2014
# License: GNU GPL v2 or higher

import unittest

from ReText.editor import documentIndentMore, documentIndentLess
from PyQt5.QtGui import QTextCursor, QTextDocument

class SettingsMock:
	tabWidth = 4
	tabInsertsSpaces = True

class TestIndentation(unittest.TestCase):
	def setUp(self):
		self.document = QTextDocument()
		self.document.setPlainText('foo\nbar\nbaz')
		self.settings = SettingsMock()

	def test_indentMore(self):
		cursor = QTextCursor(self.document)
		cursor.setPosition(4)
		documentIndentMore(self.document, cursor, self.settings)
		self.assertEqual('foo\n    bar\nbaz',
		                 self.document.toPlainText())
		cursor.setPosition(3)
		documentIndentMore(self.document, cursor, self.settings)
		self.assertEqual('foo \n    bar\nbaz',
		                 self.document.toPlainText())

	def test_indentMoreWithTabs(self):
		cursor = QTextCursor(self.document)
		self.settings.tabInsertsSpaces = False
		documentIndentMore(self.document, cursor, self.settings)
		self.assertEqual('\tfoo\nbar\nbaz', self.document.toPlainText())

	def test_indentMoreWithSelection(self):
		cursor = QTextCursor(self.document)
		cursor.setPosition(1)
		cursor.setPosition(6, QTextCursor.KeepAnchor)
		self.assertEqual('oo\u2029ba', # \u2029 is paragraph separator
		                 cursor.selectedText())
		documentIndentMore(self.document, cursor, self.settings)
		self.assertEqual('    foo\n    bar\nbaz',
		                 self.document.toPlainText())

	def test_indentLess(self):
		self.document.setPlainText('        foo')
		cursor = QTextCursor(self.document)
		cursor.setPosition(10)
		documentIndentLess(self.document, cursor, self.settings)
		self.assertEqual('    foo', self.document.toPlainText())
		documentIndentLess(self.document, cursor, self.settings)
		self.assertEqual('foo', self.document.toPlainText())

	def test_indentLessWithSelection(self):
		self.document.setPlainText('    foo\n    bar\nbaz')
		cursor = QTextCursor(self.document)
		cursor.setPosition(5)
		cursor.setPosition(11, QTextCursor.KeepAnchor)
		documentIndentLess(self.document, cursor, self.settings)
		self.assertEqual('foo\nbar\nbaz', self.document.toPlainText())

if __name__ == '__main__':
	unittest.main()
