# vim: ts=4:sw=4:expandtab

# This file is part of ReText
# Copyright: 2018 Dmitry Shachnev
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

from textwrap import dedent
from unittest import TestCase

from markdown import markdown
from markdown.extensions.codehilite import CodeHiliteExtension
from markdown.extensions.fenced_code import FencedCodeExtension
from ReText.mdx_posmap import PosMapExtension


class PosMapTest(TestCase):
    maxDiff = None
    extensionsPosMap = [
        CodeHiliteExtension(),
        FencedCodeExtension(),
        PosMapExtension()
    ]
    extensionsNoPosMap = [
        CodeHiliteExtension(),
        FencedCodeExtension()
    ]

    def test_normalUse(self):
        text = dedent("""\
        # line 1

        - line 3
        - line 4
        - line 5

        line 7
        line 8

            code block, line 10
        """)
        html = markdown(text, extensions=[PosMapExtension()])
        self.assertIn('<h1 data-posmap="1">line 1</h1>', html)
        self.assertIn('<ul data-posmap="5">', html)
        self.assertIn('<p data-posmap="8">', html)
        self.assertIn('<pre data-posmap="10"><code>code block, line 10', html)
        self.assertNotIn("posmapmarker", html)

    def test_highlightC(self):
        text = dedent("""\
        ```c
        #include <stdio.h>

        int main(int argc, char **argv)
        {
            printf("Hello, world!\\n");
        }
        ```""")
        html = markdown(text, extensions=self.extensionsPosMap)
        expected = markdown(text, extensions=self.extensionsNoPosMap)
        self.assertIn('<div class="codehilite">', html)
        self.assertMultiLineEqual(html, expected)

    def test_highlightEmptyC(self):
        text = dedent("""\
        ```c

        ```""")
        html = markdown(text, extensions=self.extensionsPosMap)
        expected = markdown(text, extensions=self.extensionsNoPosMap)
        self.assertIn('<div class="codehilite">', html)
        self.assertMultiLineEqual(html, expected)

    def test_highlightPython(self):
        text = dedent("""\
        ```python
        if __name__ == "__main__":
            print("Hello, world!")
        ```""")
        html = markdown(text, extensions=self.extensionsPosMap)
        expected = markdown(text, extensions=self.extensionsNoPosMap)
        self.assertIn('<div class="codehilite">', html)
        self.assertMultiLineEqual(html, expected)

    def test_highlightEmptyPython(self):
        text = dedent("""\
        ```python

        ```""")
        html = markdown(text, extensions=self.extensionsPosMap)
        expected = markdown(text, extensions=self.extensionsNoPosMap)
        self.assertIn('<div class="codehilite">', html)
        self.assertMultiLineEqual(html, expected)
