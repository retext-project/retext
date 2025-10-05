# vim: ts=4:sw=4:expandtab

# This file is part of ReText
# Copyright: 2014-2025 Dmitry Shachnev
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

from markups import MarkdownMarkup, ReStructuredTextMarkup
from PyQt6.QtCore import QEvent, QMimeData, Qt
from PyQt6.QtGui import QImage, QKeyEvent, QTextCursor, QTextDocument
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication

from ReText.editor import ReTextEdit, documentIndentLess, documentIndentMore

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
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
        cursor.setPosition(6, QTextCursor.MoveMode.KeepAnchor)
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
        cursor.setPosition(11, QTextCursor.MoveMode.KeepAnchor)
        documentIndentLess(self.document, cursor, self.settings)
        self.assertEqual('foo\nbar\nbaz', self.document.toPlainText())


class TestClipboardHandling(unittest.TestCase):
    class DummyReTextTab:
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
        image = QImage(80, 60, QImage.Format.Format_RGB32)
        image.fill(Qt.GlobalColor.green)
        return image

    def test_pasteText(self):
        mimeData = QMimeData()
        mimeData.setText('pasted text')
        self.editor.insertFromMimeData(mimeData)
        self.assertTrue('pasted text' in self.editor.toPlainText())

    def test_pasteHtmlConvertedToMarkdown(self):
        mimeData = QMimeData()
        mimeData.setText('plain text fallback')
        mimeData.setHtml('<p>Hello <strong>world</strong></p>')
        self.dummytab.markupClass = MarkdownMarkup
        self.editor.insertFromMimeData(mimeData)
        pasted = self.editor.toPlainText()
        self.assertIn('Hello **world**', pasted)

    def test_pasteHtmlConvertedToMarkdown_lists(self):
        mimeData = QMimeData()
        mimeData.setHtml(
            '<ul>'
            '<li>Item 1</li>'
            '<li><ul><li>Item 1.1</li></ul></li>'
            '<li>Item 2</li>'
            '</ul>'
        )
        self.dummytab.markupClass = MarkdownMarkup
        self.editor.insertFromMimeData(mimeData)
        self.assertEqual(
            self.editor.toPlainText(),
            '- Item 1\n'
            '    - Item 1.1\n'
            '- Item 2',
        )

    @patch.object(ReTextEdit, 'getImageFilename', return_value='/tmp/myimage.jpg')
    @patch.object(QImage, 'save')
    def test_pasteImage_Markdown(self, _mock_image, _mock_editor):
        mimeData = QMimeData()
        mimeData.setImageData(self._create_image())
        app.clipboard().setMimeData(mimeData)
        self.dummytab.markupClass = MarkdownMarkup
        self.dummytab.fileName = '/tmp/foo.md'

        self.editor.pasteImage()
        self.assertTrue('![myimage](myimage.jpg)' in self.editor.toPlainText())

    @patch.object(ReTextEdit, 'getImageFilename', return_value='/tmp/myimage.jpg')
    @patch.object(QImage, 'save')
    def test_pasteImage_RestructuredText(self, _mock_image, _mock_editor):
        mimeData = QMimeData()
        mimeData.setImageData(self._create_image())
        app.clipboard().setMimeData(mimeData)
        self.dummytab.markupClass = ReStructuredTextMarkup
        self.dummytab.fileName = '/tmp/foo.rst'

        self.editor.pasteImage()
        self.assertTrue('.. image:: myimage.jpg' in self.editor.toPlainText())


class TestSurround(unittest.TestCase):

    def setUp(self):
        self.p = self
        self.editor = ReTextEdit(self)
        self.document = QTextDocument()
        self.document.setPlainText('foo bar baz qux corge grault')
        self.cursor = QTextCursor(self.document)

    def getText(self, key):
        if key == Qt.Key.Key_ParenLeft:
            return '('
        if key == Qt.Key.Key_BracketLeft:
            return '['
        if key == Qt.Key.Key_Underscore:
            return '_'
        if key == Qt.Key.Key_Asterisk:
            return '*'
        if key == Qt.Key.Key_QuoteDbl:
            return '"'
        if key == Qt.Key.Key_Apostrophe:
            return '\''

    def getEvent(self, key):
        return QKeyEvent(
            QEvent.Type.KeyPress,
            key,
            Qt.KeyboardModifier.NoModifier,
            text=self.getText(key),
        )

    def test_isSurroundKey(self):
        # close keys should not start a surrounding
        self.assertFalse(self.editor.isSurroundKey(Qt.Key.Key_ParenRight))
        self.assertFalse(self.editor.isSurroundKey(Qt.Key.Key_BracketRight))

        self.assertTrue(self.editor.isSurroundKey(Qt.Key.Key_ParenLeft))
        self.assertTrue(self.editor.isSurroundKey(Qt.Key.Key_BracketLeft))
        self.assertTrue(self.editor.isSurroundKey(Qt.Key.Key_Underscore))
        self.assertTrue(self.editor.isSurroundKey(Qt.Key.Key_Asterisk))
        self.assertTrue(self.editor.isSurroundKey(Qt.Key.Key_QuoteDbl))
        self.assertTrue(self.editor.isSurroundKey(Qt.Key.Key_Apostrophe))

    def test_getCloseKey(self):
        self.assertEqual(
            self.editor.getCloseKey(self.getEvent(Qt.Key.Key_Underscore), Qt.Key.Key_Underscore),
            '_',
        )
        self.assertEqual(
            self.editor.getCloseKey(self.getEvent(Qt.Key.Key_Asterisk), Qt.Key.Key_Asterisk),
            '*',
        )
        self.assertEqual(
            self.editor.getCloseKey(self.getEvent(Qt.Key.Key_QuoteDbl), Qt.Key.Key_QuoteDbl),
            '"',
        )
        self.assertEqual(
            self.editor.getCloseKey(self.getEvent(Qt.Key.Key_Apostrophe), Qt.Key.Key_Apostrophe),
            '\'',
        )
        self.assertEqual(
            self.editor.getCloseKey(self.getEvent(Qt.Key.Key_ParenLeft), Qt.Key.Key_ParenLeft),
            ')',
        )
        self.assertEqual(
            self.editor.getCloseKey(self.getEvent(Qt.Key.Key_BracketLeft), Qt.Key.Key_BracketLeft),
            ']',
        )

    def changeCursor(self, posI, posF):
        self.cursor.setPosition(posI)
        self.cursor.setPosition(posF, QTextCursor.MoveMode.KeepAnchor)

    def test_surroundText(self):

        self.changeCursor(0, 3)
        self.editor.surroundText(
            self.cursor,
            self.getEvent(Qt.Key.Key_Underscore),
            Qt.Key.Key_Underscore,
        )
        self.assertEqual(self.document.toPlainText(), '_foo_ bar baz qux corge grault')

        self.changeCursor(6, 9)
        self.editor.surroundText(
            self.cursor,
            self.getEvent(Qt.Key.Key_Asterisk),
            Qt.Key.Key_Asterisk,
        )
        self.assertEqual(self.document.toPlainText(), '_foo_ *bar* baz qux corge grault')

        self.changeCursor(12, 15)
        self.editor.surroundText(
            self.cursor,
            self.getEvent(Qt.Key.Key_QuoteDbl),
            Qt.Key.Key_QuoteDbl,
        )
        self.assertEqual(self.document.toPlainText(), '_foo_ *bar* "baz" qux corge grault')

        self.changeCursor(18, 21)
        self.editor.surroundText(
            self.cursor,
            self.getEvent(Qt.Key.Key_Apostrophe),
            Qt.Key.Key_Apostrophe,
        )
        self.assertEqual(self.document.toPlainText(), '_foo_ *bar* "baz" \'qux\' corge grault')

        self.changeCursor(24, 29)
        self.editor.surroundText(
            self.cursor,
            self.getEvent(Qt.Key.Key_ParenLeft),
            Qt.Key.Key_ParenLeft,
        )
        self.assertEqual(self.document.toPlainText(), '_foo_ *bar* "baz" \'qux\' (corge) grault')

        self.changeCursor(32, 38)
        self.editor.surroundText(
            self.cursor,
            self.getEvent(Qt.Key.Key_BracketLeft),
            Qt.Key.Key_BracketLeft,
        )
        self.assertEqual(self.document.toPlainText(), '_foo_ *bar* "baz" \'qux\' (corge) [grault]')

class TestOrderedListMode(unittest.TestCase):

    class DummyReTextTab:
        def __init__(self):
            self.markupClass = None

        def getActiveMarkupClass(self):
            return self.markupClass

    def setUp(self):
        self.p = self

    def test_increment(self):
        editor = ReTextEdit(self)
        editor.tab = self.DummyReTextTab()
        QTest.keyClicks(editor, '1. Hello')
        QTest.keyClick(editor, Qt.Key.Key_Return)
        QTest.keyClicks(editor, 'World')
        self.assertEqual(editor.document().toPlainText(), '1. Hello\n2. World')

    def test_repeat(self):
        class TestSettings:
            orderedListMode = 'repeat'
            useFakeVim = False
        editor = ReTextEdit(self, settings=TestSettings())
        editor.tab = self.DummyReTextTab()
        QTest.keyClicks(editor, '1. Hello')
        QTest.keyClick(editor, Qt.Key.Key_Return)
        QTest.keyClicks(editor, 'World')
        self.assertEqual(editor.document().toPlainText(), '1. Hello\n1. World')

if __name__ == '__main__':
    unittest.main()
