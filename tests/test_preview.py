# vim: ts=4:sw=4:expandtab

# This file is part of ReText
# Copyright: 2018-2026 Dmitry Shachnev
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
import warnings
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QTextEdit

from ReText.editor import ReTextEdit
from ReText.preview import PreviewFrameAdapter, ReTextPreview, insertPosmapAnchors

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication.instance() or QApplication(sys.argv)

NUM_SECTIONS = 40
SOURCE = ''.join(f'## Section {i}\n\nParagraph {i}\n\n' for i in range(NUM_SECTIONS))
# Source line numbers of the blank line following each heading/paragraph
HTML = ''.join(
    f'<h2 data-posmap="{4 * i + 1}">Section {i}</h2>'
    f'<p data-posmap="{4 * i + 3}">Paragraph {i}</p>'
    for i in range(NUM_SECTIONS)
)


class InsertPosmapAnchorsTest(unittest.TestCase):

    def test_anchorAtEndOfElement(self):
        self.assertEqual(
            insertPosmapAnchors('<p data-posmap="3">a</p>'),
            '<p data-posmap="3">a<a name="posmap-3">&#8203;</a></p>')

    def test_nestedElements(self):
        html = insertPosmapAnchors('<ul data-posmap="5"><li data-posmap="4">x</li></ul>')
        self.assertEqual(
            html,
            '<ul data-posmap="5"><li data-posmap="4">x<a name="posmap-4">&#8203;</a></li>'
            '<a name="posmap-5">&#8203;</a></ul>')

    def test_unclosedElementGetsNoAnchor(self):
        # <hr> without a slash looks like an unclosed element. An anchor at the
        # wrong place would be worse than no anchor, so none is emitted.
        for html in ('<p>x</p><hr data-posmap="7">',
                     '<div><hr data-posmap="7"><p>x</p></div>',
                     '<hr data-posmap="7"><p data-posmap="9">x</p>'):
            result = insertPosmapAnchors(html)
            self.assertNotIn('posmap-7', result)

    def test_unclosedElementDoesNotAffectSiblings(self):
        self.assertEqual(
            insertPosmapAnchors('<div><hr data-posmap="7"><p data-posmap="9">x</p></div>'),
            '<div><hr data-posmap="7"><p data-posmap="9">x<a name="posmap-9">&#8203;</a></p></div>')

    def test_voidElementWithoutPosmapDoesNotAffectOthers(self):
        self.assertEqual(
            insertPosmapAnchors('<p data-posmap="3">a<br>b<img src="x.png">c</p>'),
            '<p data-posmap="3">a<br>b<img src="x.png">c<a name="posmap-3">&#8203;</a></p>')

    def test_selfClosingVoidElement(self):
        for html in ('<hr data-posmap="7"/>', '<hr data-posmap="7" />'):
            self.assertEqual(
                insertPosmapAnchors(html + '<p>x</p>'),
                html + '<a name="posmap-7">&#8203;</a><p>x</p>')

    def test_imageInParagraph(self):
        # This is what mdx_posmap generates for an image: the paragraph
        # carries the attribute, so the anchor goes after the image.
        for img in ('<img alt="i" src="a.png" />', '<img alt="i" src="a.png">'):
            self.assertEqual(
                insertPosmapAnchors(f'<p data-posmap="7">{img}</p>'),
                f'<p data-posmap="7">{img}<a name="posmap-7">&#8203;</a></p>')

    def test_selfClosingVoidElementInsideElement(self):
        self.assertEqual(
            insertPosmapAnchors('<p data-posmap="7"><img data-posmap="6" src="a.png" />x</p>'),
            '<p data-posmap="7"><img data-posmap="6" src="a.png" /><a name="posmap-6">&#8203;</a>'
            'x<a name="posmap-7">&#8203;</a></p>')

    def test_noPosmapLeavesHtmlUntouched(self):
        html = ('<!DOCTYPE html><html><body><!-- c --><p class="a">1 &amp; 2 &#169; &copy;<br/>'
                'x</p><img src="a.png"></body></html>')
        self.assertEqual(insertPosmapAnchors(html), html)

    def test_anchorAfterMultilineStartTag(self):
        self.assertEqual(
            insertPosmapAnchors('<p>a</p>\n<hr\n  data-posmap="3"\n/>\n<p>b</p>'),
            '<p>a</p>\n<hr\n  data-posmap="3"\n/><a name="posmap-3">&#8203;</a>\n<p>b</p>')

    def test_anchorsAtSameOffsetKeepOrder(self):
        self.assertEqual(
            insertPosmapAnchors('<p data-posmap="2"><img data-posmap="1" />'
                                '</p>'),
            '<p data-posmap="2"><img data-posmap="1" /><a name="posmap-1">&#8203;</a>'
            '<a name="posmap-2">&#8203;</a></p>')

    def test_entitiesArePreserved(self):
        self.assertEqual(
            insertPosmapAnchors('<p data-posmap="1">a &amp; b &#169;</p>'),
            '<p data-posmap="1">a &amp; b &#169;<a name="posmap-1">&#8203;</a></p>')


class PreviewSyncScrollTest(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', Warning)
        self.settings = MagicMock(syncScroll=True, scrollFactor=1.0)
        patch('ReText.preview.globalSettings', self.settings).start()
        self.tab = MagicMock()
        self.editBox = ReTextEdit(self.tab)
        self.editBox.setPlainText(SOURCE)
        self.editBox.resize(400, 300)
        self.editBox.show()
        app.processEvents()
        self.tab.editBox = self.editBox
        self.previews = []

    def tearDown(self):
        for preview in self.previews:
            preview.disconnectExternalSignals()
            if preview.syncscroll is not None:
                preview.syncscroll.stabilityTimer.stop()
            preview.deleteLater()
        self.editBox.deleteLater()
        patch.stopall()

    def createPreview(self):
        editBox = self.editBox

        def editorPositionToSourceLine(editorPosition):
            viewportPosition = editorPosition - editBox.verticalScrollBar().value()
            return editBox.cursorForPosition(QPoint(0, viewportPosition)).blockNumber()

        def sourceLineToEditorPosition(sourceLine):
            doc = editBox.document()
            block = doc.findBlockByNumber(sourceLine)
            return doc.documentLayout().blockBoundingRect(block).top()

        preview = ReTextPreview(self.tab, editorPositionToSourceLine, sourceLineToEditorPosition)
        preview.resize(400, 300)
        preview.show()
        self.previews.append(preview)
        return preview

    @staticmethod
    def positionMap(preview):
        result = []
        adapter = PreviewFrameAdapter(preview)
        adapter.getPositionMap(result.append)
        return result[0]

    def test_isQTextBrowserBased(self):
        self.assertIsInstance(self.createPreview(), QTextEdit)

    def test_syncscrollCreatedWhenEnabled(self):
        self.assertIsNotNone(self.createPreview().syncscroll)

    def test_syncscrollNotCreatedWhenDisabled(self):
        self.settings.syncScroll = False
        preview = self.createPreview()
        self.assertIsNone(preview.syncscroll)
        # Must not fail, and the HTML is loaded untouched
        preview.setHtml(HTML)
        preview.disconnectExternalSignals()
        self.assertEqual(self.positionMap(preview), {})

    def test_positionMapFromAnchors(self):
        preview = self.createPreview()
        preview.setHtml(HTML)
        app.processEvents()
        posmap = self.positionMap(preview)
        self.assertEqual(sorted(posmap), sorted(
            [4 * i + 1 for i in range(NUM_SECTIONS)] + [4 * i + 3 for i in range(NUM_SECTIONS)]))
        positions = [posmap[line] for line in sorted(posmap)]
        self.assertEqual(positions, sorted(positions))
        self.assertGreater(positions[-1], positions[0])

    def test_emptyAnchorsAreDropped(self):
        # Documents why the anchors need a zero-width space: Qt discards
        # empty anchors that are not followed by text.
        preview = self.createPreview()
        preview.setHtml('<p>x<a name="posmap-3"></a></p><p>y</p>')
        app.processEvents()
        self.assertEqual(self.positionMap(preview), {})

    def test_noPositionMapBeforeContentIsLoaded(self):
        preview = self.createPreview()
        self.assertEqual(self.positionMap(preview), {})

    def waitForPosmap(self, preview):
        # SyncScroll collects the position map once the content has settled
        for _ in range(100):
            app.processEvents()
            if preview.syncscroll.posmap:
                return
            QTest.qWait(20)
        self.fail('position map was not collected')

    def test_editorScrollMovesPreview(self):
        preview = self.createPreview()
        preview.setHtml(HTML)
        self.waitForPosmap(preview)
        self.assertTrue(preview.syncscroll.isActive())
        editorBar = self.editBox.verticalScrollBar()
        previewBar = preview.verticalScrollBar()
        self.assertGreater(editorBar.maximum(), 0)
        self.assertGreater(previewBar.maximum(), 0)

        editorBar.setValue(editorBar.maximum() // 2)
        middle = previewBar.value()
        self.assertGreater(middle, 0)

        editorBar.setValue(editorBar.maximum())
        end = previewBar.value()
        self.assertGreater(end, middle)

        editorBar.setValue(0)
        self.assertLess(previewBar.value(), middle)

    def test_previewScrollMovesEditor(self):
        preview = self.createPreview()
        preview.setHtml(HTML)
        self.waitForPosmap(preview)
        editorBar = self.editBox.verticalScrollBar()
        previewBar = preview.verticalScrollBar()
        # Let the settling logic triggered by the load finish
        QTest.qWait(700)
        app.processEvents()
        previewBar.setValue(previewBar.maximum() // 2)
        self.assertGreater(editorBar.value(), 0)
        before = editorBar.value()
        previewBar.setValue(previewBar.maximum())
        self.assertGreater(editorBar.value(), before)

    def test_disconnectStopsSync(self):
        preview = self.createPreview()
        preview.setHtml(HTML)
        self.waitForPosmap(preview)
        preview.disconnectExternalSignals()
        previewBar = preview.verticalScrollBar()
        before = previewBar.value()
        editorBar = self.editBox.verticalScrollBar()
        editorBar.setValue(editorBar.maximum())
        self.assertEqual(previewBar.value(), before)
        # Already disconnected, so tearDown must not disconnect again
        preview.syncscroll.stabilityTimer.stop()
        self.previews.remove(preview)
        preview.deleteLater()


if __name__ == '__main__':
    unittest.main()
