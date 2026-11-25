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
This test actually instantiates a QWebEngineView and calls setHtml() on it,
which starts Chromium's renderer. In some sandboxed/headless environments
(no GPU, no suitable seccomp/namespace permissions, missing shared memory,
etc.) this can abort the whole Python process rather than raising a
catchable exception -- which would take down the entire test suite, not
just this one test file. To keep `python -m unittest discover -s tests`
always safe to run, it is skipped unless explicitly requested:

    RETEXT_TEST_WEBENGINE_RENDERING=1 QT_QPA_PLATFORM=offscreen \
        python3 -m unittest tests.test_webenginepreview_syncscroll -v
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
from ReText.tab import ReTextWebEnginePreview

QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
app = QApplication.instance() or QApplication(sys.argv)

RUN_RENDERING_TESTS = os.environ.get('RETEXT_TEST_WEBENGINE_RENDERING') == '1'
SKIP_REASON = ('set RETEXT_TEST_WEBENGINE_RENDERING=1 to run tests that render '
              'real content in a QWebEngineView (can abort the whole test '
              'process in some sandboxed/headless environments)')


class FakeTab(QWidget):
    fileNameChanged = pyqtSignal()

    def __init__(self, editBox):
        super().__init__()
        self.editBox = editBox
        self.fileName = None
        self.p = None

    def openSourceFile(self, path):
        return False


@unittest.skipUnless(ReTextWebEnginePreview is not None and RUN_RENDERING_TESTS, SKIP_REASON)
class WebEnginePreviewSyncScrollTeardownTest(unittest.TestCase):
    '''
    Regression test for a crash where SyncScroll's stabilityTimer kept
    running after disconnectExternalSignals()+deleteLater(), and firing
    later (it is a 500ms QTimer) called back into the by-then-deleted
    page, raising "RuntimeError: wrapped C/C++ object of type
    ReTextWebEnginePage has been deleted" and aborting the whole process
    via Qt's fatal message handler. Reproducible any time a WebEngine
    preview is torn down shortly after a reload settles (closing a tab,
    switching away from WebEngine, rebuildPreviewBox() in general).
    '''

    def setUp(self):
        warnings.simplefilter('ignore', Warning)
        self.settings = MagicMock(handleWebLinks=False)
        patch('ReText.webenginepreview.globalSettings', self.settings).start()
        self.previews = []

    def tearDown(self):
        for preview in self.previews:
            preview.deleteLater()
        for _ in range(10):
            app.processEvents()
            QTest.qWait(10)
        patch.stopall()

    def createPreview(self):
        tab = FakeTab(None)
        editBox = ReTextEdit(tab)
        tab.editBox = editBox
        self.previews.append(editBox)  # keep a reference alive for tearDown
        preview = ReTextWebEnginePreview(tab, lambda pos: 0, lambda line: 0)
        self.previews.append(preview)
        return preview

    def waitForStabilityTimerToStart(self, preview):
        for _ in range(150):
            app.processEvents()
            if preview.syncscroll.stabilityTimer.isActive():
                return
            QTest.qWait(20)
        self.fail('stabilityTimer never started')

    def test_disconnectStopsStabilityTimerToAvoidCrashAfterDeletion(self):
        preview = self.createPreview()
        preview.setHtml('<p>Hello</p>', QUrl())
        self.waitForStabilityTimerToStart(preview)

        preview.disconnectExternalSignals()
        self.assertFalse(preview.syncscroll.stabilityTimer.isActive())

        # Already disconnected, so tearDown must not disconnect again.
        self.previews.remove(preview)
        preview.deleteLater()
        # If the timer had not been stopped, it would fire about now and
        # crash the whole process instead of just failing this assertion.
        for _ in range(80):
            app.processEvents()
            QTest.qWait(10)


if __name__ == '__main__':
    unittest.main()
