# vim: ts=4:sw=4:expandtab
#
# This file is part of ReText
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

import re

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor


class _ListIndentPreprocessor(Preprocessor):
    """Normalise indentation for nested list items."""

    LIST_ITEM_RE = re.compile(r'^(?P<indent>[ \t]+)(?P<bullet>(?:[-+*]|\d+\.))\s+')

    def run(self, lines):
        normalised = []
        for line in lines:
            match = self.LIST_ITEM_RE.match(line)
            if match:
                indent_len = len(match.group('indent').expandtabs(4))
                if indent_len and indent_len % 4:
                    indent_len += 4 - (indent_len % 4)
                if 0 < indent_len < 4:
                    indent_len = 4
                replacement = ' ' * indent_len
                line = replacement + line[len(match.group('indent')):]
            normalised.append(line)
        return normalised


class TabLengthExtension(Extension):
    """Treat short indents as nested list markers."""

    def extendMarkdown(self, md):
        md.registerExtension(self)
        preprocessor = _ListIndentPreprocessor(md)
        md.preprocessors.register(preprocessor, 'retext_tablength', 31)


def makeExtension(**kwargs):
    return TabLengthExtension(**kwargs)
