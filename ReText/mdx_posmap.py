'''
Position Map Extension for Python-Markdown
==========================================

This extension adds data-posmap attributes to the generated HTML elements that
can be used to relate HTML elements to the corresponding lines in the markdown
input file.

Note: the line number stored in the data-posmap attribute corresponds to the
      empty line *after* the markdown block that the HTML was generated from.

Copyright 2016 [Maurice van der Pot](griffon26@kfk4ever.com)
          2017-2024 Dmitry Shachnev

License: [BSD](http://www.opensource.org/licenses/bsd-license.php)

'''

import re
from xml.etree.ElementTree import SubElement

from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
from markdown.extensions.codehilite import CodeHilite
from markdown.preprocessors import Preprocessor
from markdown.util import HTML_PLACEHOLDER_RE

try:
    from pymdownx.highlight import Highlight
except ImportError:
    Highlight = None


POSMAP_MARKER_RE = re.compile(r'__posmapmarker__\d+\n\n')


class PosMapExtension(Extension):
    """ Position Map Extension for Python-Markdown. """

    def extendMarkdown(self, md):
        """ Insert the PosMapExtension blockprocessor before any other
            extensions to make sure our own markers, inserted by the
            preprocessor, are removed before any other extensions get confused
            by them.
        """
        md.preprocessors.register(PosMapMarkPreprocessor(md), 'posmap_mark', 50)
        md.preprocessors.register(PosMapCleanPreprocessor(md), 'posmap_clean', 5)
        md.parser.blockprocessors.register(PosMapBlockProcessor(md.parser), 'posmap', 150)

        # Monkey patch CodeHilite constructor to remove the posmap markers from
        # text before highlighting it
        orig_codehilite_init = CodeHilite.__init__

        def new_codehilite_init(self, src=None, *args, **kwargs):
            src = POSMAP_MARKER_RE.sub('', src)
            orig_codehilite_init(self, src=src, *args, **kwargs)
        CodeHilite.__init__ = new_codehilite_init

        # Same for PyMdown Extensions if it is available
        if Highlight is not None:
            orig_highlight_highlight = Highlight.highlight

            def new_highlight_highlight(self, src, *args, **kwargs):
                src = POSMAP_MARKER_RE.sub('', src)
                return orig_highlight_highlight(self, src, *args, **kwargs)
            Highlight.highlight = new_highlight_highlight


class PosMapMarkPreprocessor(Preprocessor):
    """ PosMapMarkPreprocessor - insert __posmapmarker__linenr entries at each empty line """

    def run(self, lines):
        new_text = []
        for i, line in enumerate(lines):
            new_text.append(line)
            if line == '':
                # Do not insert markers in the middle of an indented block.
                if 0 < i < len(lines) - 1:
                    # Find the closest lines before and after this one that have
                    # non-whitespace characters, and check if they are indented.
                    i_prev = i - 1
                    while i_prev > 0 and lines[i_prev].strip() == "":
                        i_prev -= 1
                    i_next = i + 1
                    while i_next < len(lines) - 1 and lines[i_next].strip() == "":
                        i_next += 1
                    if lines[i_prev].startswith(" ") and lines[i_next].startswith(" "):
                        continue

                new_text.append(f'__posmapmarker__{i}')
                new_text.append('')
        return new_text

class PosMapCleanPreprocessor(Preprocessor):
    """ PosMapCleanPreprocessor - remove __posmapmarker__linenr entries that
        accidentally ended up in the htmlStash. This could have happened
        because they were inside html tags or a fenced code block.
    """

    def run(self, lines):

        for i in range(self.md.htmlStash.html_counter):
            block = self.md.htmlStash.rawHtmlBlocks[i]
            block = re.sub(POSMAP_MARKER_RE, '', block)
            self.md.htmlStash.rawHtmlBlocks[i] = block

        return lines


class PosMapBlockProcessor(BlockProcessor):
    """ PosMapBlockProcessor - remove each marker and add a data-posmap
        attribute to the previous HTML element
    """

    def test(self, parent, block):
        return block.startswith('__posmapmarker__')

    def run(self, parent, blocks):
        block = blocks.pop(0)
        line_nr = block.split('__')[2]
        last_child = self.lastChild(parent)
        if last_child is not None:
            # Avoid setting the attribute on HTML placeholders, because it
            # would interfere with later replacement with literal HTML
            # fragments. In this case just add an empty <p> with the attribute.
            if last_child.text and re.match(HTML_PLACEHOLDER_RE, last_child.text):
                last_child = SubElement(parent, 'p')
            last_child.set('data-posmap', line_nr)

def makeExtension(*args, **kwargs):
    return PosMapExtension(*args, **kwargs)

