# vim: ts=4:sw=4:expandtab

# This file is part of ReText
# Copyright: 2026 ReText project
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

'''
These tests actually instantiate a QWebEngineView and call setHtml() on it,
which starts Chromium's renderer. In some sandboxed/headless environments
(no GPU, no suitable seccomp/namespace permissions, missing shared memory,
etc.) this can abort the whole Python process rather than raising a
catchable exception -- which would take down the entire test suite, not
just this one test file. To keep `python -m unittest discover -s tests`
always safe to run, these tests are skipped unless explicitly requested:

    RETEXT_TEST_WEBENGINE_RENDERING=1 QT_QPA_PLATFORM=offscreen \
        python3 -m unittest tests.test_webenginepreview_headings -v
'''

import os
import sys
import unittest
import warnings
from unittest.mock import MagicMock, patch

from PyQt6.QtCore import Qt, QUrl, pyqtSignal
from PyQt6.QtTest import QTest
from PyQt6.QtWidgets import QApplication, QWidget

from ReText.editor import ReTextEdit
from ReText.headingcollapse import buildHeaders
from ReText.tab import ReTextWebEnginePreview

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication.instance() or QApplication(sys.argv)

RUN_RENDERING_TESTS = os.environ.get('RETEXT_TEST_WEBENGINE_RENDERING') == '1'
SKIP_REASON = ('set RETEXT_TEST_WEBENGINE_RENDERING=1 to run tests that render '
              'real content in a QWebEngineView (can abort the whole test '
              'process in some sandboxed/headless environments)')

HTML_BODY = (
    '<h1>Title 1</h1><p>Intro paragraph.</p>'
    '<h2>Sub-title A</h2><p>Paragraph A.</p>'
    '<h2>Sub-title A</h2><p>Paragraph A again (duplicate heading text).</p>'
    '<h2>Sub-title B</h2><p>Paragraph B.</p>'
)

BASE_URL = QUrl.fromLocalFile('/tmp/')


class FakeTab(QWidget):
    fileNameChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.editBox = None
        self.previewBox = None
        self.fileName = None
        self.p = None

    def openSourceFile(self, path):
        return False


@unittest.skipUnless(ReTextWebEnginePreview is not None and RUN_RENDERING_TESTS, SKIP_REASON)
class WebEngineHeadingCollapseTest(unittest.TestCase):

    def setUp(self):
        warnings.simplefilter('ignore', Warning)
        self.settings = MagicMock(handleWebLinks=False)
        patch('ReText.webenginepreview.globalSettings', self.settings).start()
        self.tab = FakeTab()
        self.editBox = ReTextEdit(self.tab)
        self.tab.editBox = self.editBox
        self.previews = []

    def tearDown(self):
        for preview in self.previews:
            preview.disconnectExternalSignals()
            preview.deleteLater()
        self.editBox.deleteLater()
        self.tab.deleteLater()
        # Give WebEngine a chance to actually finish tearing down this
        # test's renderer resources before the next test's setUp creates
        # a new QWebEngineView.
        for _ in range(10):
            app.processEvents()
            QTest.qWait(10)
        patch.stopall()

    def createPreview(self):
        preview = ReTextWebEnginePreview(self.tab, lambda pos: 0, lambda line: 0)
        self.tab.previewBox = preview
        self.previews.append(preview)
        return preview

    def evalJs(self, preview, script):
        result = []
        preview.page().runJavaScript(script, lambda value: result.append((value,)))
        for _ in range(150):
            app.processEvents()
            if result:
                return result[0][0]
            QTest.qWait(20)
        self.fail('runJavaScript callback did not fire')

    def loadSections(self, preview, initialCollapsed):
        # Mirrors what ReTextTab.getHtmlFromConverted() does on every real
        # preview regeneration: bake the preview's *current* (possibly
        # already-mutated-by-the-user) state into a fresh headers block.
        headers = buildHeaders(initialCollapsed, preview.headingCollapseState)
        preview.setHtml(headers + HTML_BODY, BASE_URL)
        for _ in range(150):
            app.processEvents()
            QTest.qWait(20)
            if self.evalJs(preview, 'typeof window.retextSetAllCollapsed') == 'function':
                return
        self.fail('preview did not finish loading the injected script')

    def isHidden(self, preview, selector):
        return self.evalJs(preview, f'document.querySelector("{selector}").style.display === "none"')

    def clickToggle(self, preview, nth=0):
        self.evalJs(
            preview,
            f'document.querySelectorAll(".retext-heading-toggle")[{nth}].click(); "clicked"',
        )
        for _ in range(50):
            app.processEvents()
            QTest.qWait(10)

    def test_initialStateCollapsedHidesAllSections(self):
        preview = self.createPreview()
        self.loadSections(preview, initialCollapsed=True)
        self.assertTrue(self.isHidden(preview, 'p'))

    def test_initialStateExpandedShowsEverything(self):
        preview = self.createPreview()
        self.loadSections(preview, initialCollapsed=False)
        self.assertFalse(self.isHidden(preview, 'p'))

    def test_newHeadingTakesInitialState(self):
        preview = self.createPreview()
        self.loadSections(preview, initialCollapsed=True)
        # No toggles yet: every heading is "new" and must follow the
        # initial-state setting, not some leftover default.
        self.assertEqual(preview.headingCollapseState.overrides, {})

    def test_toggleTogglesStateAndPersistsAcrossRegeneration(self):
        preview = self.createPreview()
        self.loadSections(preview, initialCollapsed=False)
        self.clickToggle(preview, 0)  # "Title 1" is the first heading
        self.assertEqual(preview.headingCollapseState.overrides.get('Title 1'), True)

        # Simulate a regeneration: same headings, fresh page load, with
        # the state baked in from the (now-mutated) Python-side object.
        self.loadSections(preview, initialCollapsed=False)
        self.assertTrue(self.isHidden(preview, 'p'))
        self.assertEqual(preview.headingCollapseState.overrides.get('Title 1'), True)

    def test_duplicateSiblingHeadingsAreIndependentlyToggleable(self):
        preview = self.createPreview()
        self.loadSections(preview, initialCollapsed=False)
        # Two "Sub-title A" headings exist; they must get distinct ids,
        # and toggling one must not affect the other's state.
        self.clickToggle(preview, 1)
        ids = list(preview.headingCollapseState.overrides)
        self.assertEqual(len(ids), 1)
        self.assertTrue(ids[0] == 'Title 1 > Sub-title A' or ids[0].startswith('Title 1 > Sub-title A#'))

    def test_collapseAllUpdatesPythonStateAndPersistsAcrossRegeneration(self):
        preview = self.createPreview()
        self.loadSections(preview, initialCollapsed=False)
        self.assertFalse(self.isHidden(preview, 'p'))

        preview.setAllHeadingsCollapsed(True)
        self.assertIs(preview.headingCollapseState.bulkState, True)
        for _ in range(50):
            app.processEvents()
            QTest.qWait(10)
        self.assertTrue(self.isHidden(preview, 'p'))

        # A regeneration after "Collapse all" must keep everything
        # collapsed, even though no individual heading was ever clicked.
        self.loadSections(preview, initialCollapsed=False)
        self.assertTrue(self.isHidden(preview, 'p'))
        self.assertIs(preview.headingCollapseState.bulkState, True)

    def test_expandAllAfterCollapseAllOverridesIt(self):
        preview = self.createPreview()
        self.loadSections(preview, initialCollapsed=False)
        preview.setAllHeadingsCollapsed(True)
        preview.setAllHeadingsCollapsed(False)
        self.assertIs(preview.headingCollapseState.bulkState, False)
        self.assertEqual(preview.headingCollapseState.overrides, {})

        self.loadSections(preview, initialCollapsed=False)
        self.assertFalse(self.isHidden(preview, 'p'))


if __name__ == '__main__':
    unittest.main()
