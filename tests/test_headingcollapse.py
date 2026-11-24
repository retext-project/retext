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

import json
import unittest

from PyQt6.QtCore import QUrl

from ReText.headingcollapse import HeadingCollapseState, buildHeaders, parseToggleUrl


class HeadingCollapseStateTest(unittest.TestCase):

    def test_toggleRecordsOverride(self):
        state = HeadingCollapseState()
        state.toggle('Title', True)
        self.assertEqual(state.overrides, {'Title': True})
        self.assertIsNone(state.bulkState)

    def test_setBulkClearsOverrides(self):
        state = HeadingCollapseState()
        state.toggle('Title', True)
        state.setBulk(False)
        self.assertEqual(state.overrides, {})
        self.assertIs(state.bulkState, False)

    def test_clearResetsEverything(self):
        state = HeadingCollapseState()
        state.toggle('Title', True)
        state.setBulk(True)
        state.clear()
        self.assertEqual(state.overrides, {})
        self.assertIsNone(state.bulkState)

    def test_toJsonBlobRoundTrips(self):
        state = HeadingCollapseState()
        state.toggle('Title 1 > Sub-title', True)
        blob = state.toJsonBlob(False)
        data = json.loads(blob)
        self.assertEqual(data['overrides'], {'Title 1 > Sub-title': True})
        self.assertIsNone(data['bulkState'])
        self.assertFalse(data['initialCollapsed'])

    def test_toJsonBlobEscapesScriptClosingTag(self):
        state = HeadingCollapseState()
        state.toggle('</script><script>alert(1)</script>', True)
        blob = state.toJsonBlob(True)
        self.assertNotIn('</script>', blob)
        self.assertNotIn('<script>', blob)
        # The escaped blob must still be valid, equivalent JSON once a
        # JS engine (or, here, json.loads on the un-escaped form) parses it.
        unescaped = blob.replace('\\u003c', '<').replace('\\u003e', '>').replace('\\u0026', '&')
        data = json.loads(unescaped)
        self.assertIn('</script><script>alert(1)</script>', data['overrides'])


class ParseToggleUrlTest(unittest.TestCase):

    def test_parsesIdAndCollapsedState(self):
        url = QUrl('retext-heading-toggle://x?id=Title%201&state=1')
        self.assertEqual(parseToggleUrl(url), ('Title 1', True))

    def test_parsesExpandedState(self):
        url = QUrl('retext-heading-toggle://x?id=Title&state=0')
        self.assertEqual(parseToggleUrl(url), ('Title', False))

    def test_decodesPathSeparator(self):
        url = QUrl('retext-heading-toggle://x?id=Title%201%20%3E%20Sub-title&state=1')
        self.assertEqual(parseToggleUrl(url), ('Title 1 > Sub-title', True))

    def test_ignoresOtherSchemes(self):
        url = QUrl('https://example.com/?id=Title&state=1')
        self.assertIsNone(parseToggleUrl(url))

    def test_returnsNoneWithoutRequiredParameters(self):
        url = QUrl('retext-heading-toggle://x?id=Title')
        self.assertIsNone(parseToggleUrl(url))


class BuildHeadersTest(unittest.TestCase):

    def test_includesStyleAndScript(self):
        headers = buildHeaders(True, HeadingCollapseState())
        self.assertIn('<style', headers)
        self.assertIn('retext-heading-toggle', headers)
        self.assertIn('"initialCollapsed": true', headers)

    def test_bakesInOverrides(self):
        state = HeadingCollapseState()
        state.toggle('Title', False)
        headers = buildHeaders(True, state)
        self.assertIn('"Title": false', headers)


if __name__ == '__main__':
    unittest.main()
