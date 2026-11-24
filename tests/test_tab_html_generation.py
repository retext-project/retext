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

import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from ReText.headingcollapse import HeadingCollapseState
from ReText.tab import ReTextTab


class FakeConverted:
    """ Returns custom_headers verbatim, so tests can inspect exactly what
    getHtmlFromConverted() decided to inject, without depending on how
    python-markups assembles the rest of the document. """

    def get_whole_html(self, custom_headers='', include_stylesheet=True, fallback_title='', webenv=False):
        return custom_headers

    def get_document_title(self):
        return 'Title'


def makeFakeTab():
    previewBox = SimpleNamespace(headingCollapseState=HeadingCollapseState())
    parent = SimpleNamespace(ss=None)
    return SimpleNamespace(
        p=parent,
        previewBox=previewBox,
        cssFileExists=False,
        getBaseName=lambda: 'document',
    )


class GetHtmlFromConvertedCollapsibleHeadingsTest(unittest.TestCase):

    def setUp(self):
        self.settings = MagicMock(collapsibleHeadings=False, initialSectionState='collapsed',
                                  scrollFactor=1.0)
        patch('ReText.tab.globalSettings', self.settings).start()

    def tearDown(self):
        patch.stopall()

    def call(self, **kwargs):
        return ReTextTab.getHtmlFromConverted(makeFakeTab(), FakeConverted(), **kwargs)

    def test_disabledSettingProducesUnchangedHtml_webEnginePreview(self):
        html = self.call(preview=True, isWebEnginePreview=True)
        self.assertNotIn('retext-heading-toggle', html)

    def test_disabledSettingProducesUnchangedHtml_textBrowserPreview(self):
        html = self.call(preview=True, isWebEnginePreview=False)
        self.assertNotIn('retext-heading-toggle', html)

    def test_enabledSettingButTextBrowserPreviewInjectsNothing(self):
        self.settings.collapsibleHeadings = True
        html = self.call(preview=True, isWebEnginePreview=False)
        self.assertNotIn('retext-heading-toggle', html)

    def test_enabledSettingAndWebEnginePreviewInjectsScript(self):
        self.settings.collapsibleHeadings = True
        html = self.call(preview=True, isWebEnginePreview=True)
        self.assertIn('retext-heading-toggle', html)
        self.assertIn('"initialCollapsed": true', html)

    def test_expandedInitialState(self):
        self.settings.collapsibleHeadings = True
        self.settings.initialSectionState = 'expanded'
        html = self.call(preview=True, isWebEnginePreview=True)
        self.assertIn('"initialCollapsed": false', html)

    def test_exportNeverInjectsEvenWhenEnabled(self):
        self.settings.collapsibleHeadings = True
        # preview defaults to False, matching getDocumentForExport()
        html = self.call(isWebEnginePreview=True)
        self.assertNotIn('retext-heading-toggle', html)

    def test_exportNeverInjectsEvenWhenWebEnginePreviewFlagIsStale(self):
        # Belt-and-suspenders: even if a caller passed isWebEnginePreview=True
        # without preview=True, nothing should be injected.
        self.settings.collapsibleHeadings = True
        html = self.call(preview=False, isWebEnginePreview=True)
        self.assertNotIn('retext-heading-toggle', html)


if __name__ == '__main__':
    unittest.main()
