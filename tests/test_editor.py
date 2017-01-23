# vim: ts=8:sts=8:sw=8:noexpandtab

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

import sys
import unittest
from unittest.mock import patch

from ReText.editor import ReTextEdit
from ReText.editor import documentIndentMore, documentIndentLess
from PyQt5.QtGui import QImage, QTextCursor, QTextDocument
from PyQt5.QtCore import Qt, QMimeData
from PyQt5.QtWidgets import QApplication
from markups import MarkdownMarkup, ReStructuredTextMarkup

if hasattr(Qt, 'AA_ShareOpenGLContexts'):
	QApplication.setAttribute(Qt.AA_ShareOpenGLContexts)
# Keep a reference so it is not garbage collected
app = QApplication.instance() or QApplication(sys.argv)

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


class TestClipboardHandling(unittest.TestCase):
	class DummyReTextTab():
		def __init__(self):
			self.markupClass = None

		def getActiveMarkupClass(self):
			return self.markupClass

	def setUp(self):
		self.p = self
		self.editor = ReTextEdit(self)
		self.dummytab = self.DummyReTextTab()
		self.editor.tab = self.dummytab

	def _create_image(self):
		image = QImage(80, 60, QImage.Format_RGB32)
		image.fill(Qt.green)
		return image

	def test_allowTextOnClipboard(self):
		mimeData = QMimeData()
		mimeData.setText('hello')
		self.assertTrue(self.editor.canInsertFromMimeData(mimeData))

	def test_allowImageOnClipboard(self):
		mimeData = QMimeData()
		mimeData.setImageData(self._create_image())
		self.assertTrue(self.editor.canInsertFromMimeData(mimeData))

	def test_pasteText(self):
		mimeData = QMimeData()
		mimeData.setText('pasted text')
		self.editor.insertFromMimeData(mimeData)
		self.assertTrue('pasted text' in self.editor.toPlainText())

	@patch.object(ReTextEdit, 'getImageFilenameAndLink', return_value=('/tmp/myimage.jpg', 'myimage.jpg'))
	@patch.object(QImage, 'save')
	def test_pasteImage_Markdown(self, _mock_image, _mock_editor):
		mimeData = QMimeData()
		mimeData.setImageData(self._create_image())
		self.dummytab.markupClass = MarkdownMarkup

		self.editor.insertFromMimeData(mimeData)
		self.assertTrue('![myimage](myimage.jpg)' in self.editor.toPlainText())

	@patch.object(ReTextEdit, 'getImageFilenameAndLink', return_value=('/tmp/myimage.jpg', 'myimage.jpg'))
	@patch.object(QImage, 'save')
	def test_pasteImage_RestructuredText(self, _mock_image, _mock_editor):
		mimeData = QMimeData()
		mimeData.setImageData(self._create_image())
		self.dummytab.markupClass = ReStructuredTextMarkup

		self.editor.insertFromMimeData(mimeData)
		self.assertTrue('.. image:: myimage.jpg' in self.editor.toPlainText())

if __name__ == '__main__':
	unittest.main()
