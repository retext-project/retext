'''
Position Map Extension for Python-Markdown
==========================================

This extension adds data-posmap attributes to the generated HTML elements that
can be used to relate HTML elements to the corresponding lines in the markdown
input file.

Note: the line number stored in the data-posmap attribute corresponds to the
      empty line *after* the markdown block that the HTML was generated from.

Copyright 2016 [Maurice van der Pot](griffon26@kfk4ever.com)

License: [BSD](http://www.opensource.org/licenses/bsd-license.php)

'''

from __future__ import unicode_literals

import re

from markdown.blockprocessors import BlockProcessor
from markdown.extensions import Extension
from markdown.extensions.codehilite import CodeHilite
from markdown.preprocessors import Preprocessor
from markdown.util import etree, HTML_PLACEHOLDER_RE

POSMAP_MARKER_RE = re.compile(r'__posmapmarker__\d+\n\n')


class PosMapExtension(Extension):
    """ Position Map Extension for Python-Markdown. """

    def extendMarkdown(self, md, md_globals):
        """ Insert the PosMapExtension blockprocessor before any other
            extensions to make sure our own markers, inserted by the
            preprocessor, are removed before any other extensions get confused
            by them.
        """
        md.preprocessors.add('posmap_mark', PosMapMarkPreprocessor(md), '_begin')
        md.preprocessors.add('posmap_clean', PosMapCleanPreprocessor(md), '_end')
        md.parser.blockprocessors.add('posmap', PosMapBlockProcessor(md.parser), '_begin')

        # Monkey patch CodeHilite constructor to remove the posmap markers from
        # text before highlighting it
        orig_codehilite_init = CodeHilite.__init__

        def new_codehilite_init(self, src=None, *args, **kwargs):
            src = POSMAP_MARKER_RE.sub('', src)
            orig_codehilite_init(self, src=src, *args, **kwargs)
        CodeHilite.__init__ = new_codehilite_init


class PosMapMarkPreprocessor(Preprocessor):
    """ PosMapMarkPreprocessor - insert __posmapmarker__linenr entries at each empty line """

    def run(self, lines):
        new_text = []
        for i, line in enumerate(lines):
            new_text.append(line)
            if line == '':
                new_text.append('__posmapmarker__%d' % i)
                new_text.append('')
        return new_text

class PosMapCleanPreprocessor(Preprocessor):
    """ PosMapCleanPreprocessor - remove __posmapmarker__linenr entries that
        accidentally ended up in the htmlStash. This could have happened
        because they were inside html tags or a fenced code block.

        The codehilite extension wraps this line into a span, so handle that
        case too (see https://github.com/retext-project/retext/issues/299).
    """

    def run(self, lines):

        for i in range(self.markdown.htmlStash.html_counter):
            block = self.markdown.htmlStash.rawHtmlBlocks[i]
            if isinstance(block, tuple):
                # Python-Markdown 2.x uses (html, safe_mode) tuples
                html, safe = block
                block = re.sub(POSMAP_MARKER_RE, '', html), safe
            else:
                block = re.sub(POSMAP_MARKER_RE, '', block)
            self.markdown.htmlStash.rawHtmlBlocks[i] = block

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
        if last_child != None:
            # Avoid setting the attribute on HTML placeholders, because it
            # would interfere with later replacement with literal HTML
            # fragments. In this case just add an empty <p> with the attribute.
            if last_child.text and re.match(HTML_PLACEHOLDER_RE, last_child.text):
                last_child = etree.SubElement(parent, 'p')
            last_child.set('data-posmap', line_nr)

def makeExtension(*args, **kwargs):
    return PosMapExtension(*args, **kwargs)

